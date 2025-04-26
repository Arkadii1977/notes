from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Ellipse
from kivy.clock import Clock
from datetime import datetime
import os
import json
from typing import TextIO


class SamsungNotesApp(App):
    def __init__(self):
        super().__init__()
        self.notes = []
        self.current_note = None
        self.theme = 'light'
        self.colors = {
            'light': {
                'bg': '#F7F9FC',
                'text': '#1A1A1A',
                'card': '#FFFFFF',
                'card_pressed': '#F0F0F0',
                'primary': '#007AFF',
                'secondary': '#34C759',
                'header': '#E8ECEF',
                'shadow': '#0000001A',
                'border': '#E0E4E8'
            },
            'dark': {
                'bg': '#1C2526',
                'text': '#E6ECEF',
                'card': '#2A3436',
                'card_pressed': '#3A4446',
                'primary': '#3399FF',
                'secondary': '#40C78F',
                'header': '#2F3A3C',
                'shadow': '#0000004D',
                'border': '#3A4648'
            }
        }

        self.main_layout = None
        self.header = None
        self.header_label = None
        self.scroll_view = None
        self.notes_grid = None
        self.add_btn = None
        self.editor_title = None
        self.editor_content = None
        self.delete_panel = None
        self.selected_cards = set()
        self.is_selection_mode = False
        self.touch_start_time = 0

        self.load_data()

    def build(self):
        self.root_layout = FloatLayout()
        self.main_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)

        # Header
        self.header = BoxLayout(size_hint=(1, None), height=dp(64), padding=(dp(20), 0))
        self.header_label = Label(
            text=f"Заметки\n{len(self.notes)} заметок",
            halign='left',
            valign='center',
            font_size=dp(20),
            bold=True,
            markup=True,
            font_name='Arial'
        )
        self.header.add_widget(self.header_label)

        # Notes area
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.notes_grid = GridLayout(
            cols=2,
            spacing=dp(12),
            size_hint_y=None,
            padding=(dp(16), dp(16), dp(16), dp(16)),
            row_default_height=dp(180),
            row_force_default=True
        )
        self.notes_grid.bind(
            minimum_height=self.notes_grid.setter('height'),
            width=self._update_note_cards,
            size=self._update_note_cards_on_size
        )
        self.scroll_view.add_widget(self.notes_grid)

        # Add button
        self.add_btn = Button(
            text='+',
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={'right': 0.92, 'bottom': 0.08},
            background_normal='',
            background_color=get_color_from_hex(self.colors[self.theme]['primary']),
            color=(1, 1, 1, 1),
            font_size=dp(28),
            bold=True,
            font_name='Arial'
        )
        self.add_btn.bind(on_press=self.show_editor)

        self.main_layout.add_widget(self.header)
        self.main_layout.add_widget(self.scroll_view)
        self.root_layout.add_widget(self.main_layout)
        self.root_layout.add_widget(self.add_btn)

        self.update_theme()
        Clock.schedule_once(lambda dt: self._update_note_cards(self.notes_grid, self.notes_grid.width), 0.1)
        return self.root_layout

    def _update_note_cards_on_size(self, instance, size):
        """Update note cards when the grid size changes"""
        self._update_note_cards(instance, instance.width)

    def _update_note_cards(self, instance, width):
        """Updates note cards with proper sizing and styling"""
        if width < 1:
            return

        self.notes_grid.clear_widgets()
        card_width = (width - dp(44)) / 2

        for note in sorted(self.notes, key=lambda x: x['date'], reverse=True):
            # Create note card
            card = BoxLayout(
                orientation='vertical',
                size_hint=(None, None),
                size=(card_width, dp(180)),
                padding=dp(12),
                spacing=dp(8)
            )

            # Draw card background with shadow and rounded corners
            with card.canvas.before:
                # Shadow
                Color(*get_color_from_hex(self.colors[self.theme]['shadow']))
                card.shadow = RoundedRectangle(
                    pos=(card.x + dp(2), card.y - dp(2)),
                    size=(card_width, dp(180)),
                    radius=[dp(12)]
                )
                # Card background
                Color(*get_color_from_hex(self.colors[self.theme]['card']))
                card.bg = RoundedRectangle(
                    pos=card.pos,
                    size=(card_width, dp(180)),
                    radius=[dp(12)]
                )
                # Border
                Color(*get_color_from_hex(self.colors[self.theme]['border']))
                card.border = Line(
                    rounded_rectangle=(card.x, card.y, card_width, dp(180), dp(12)),
                    width=1
                )

            # Checkbox indicator (initially invisible)
            with card.canvas.after:
                Color(0, 0, 0, 0)
                card.checkmark_bg = Ellipse(
                    pos=(card.x + card_width - dp(32), card.y + card.height - dp(32)),
                    size=(dp(28), dp(28))
                )
                card.checkmark = Label(
                    text='',
                    font_size=dp(18),
                    font_name='Arial',
                    color=(1, 1, 1, 1),
                    pos=(card.x + card_width - dp(32) + dp(5), card.y + card.height - dp(32) + dp(3)),
                    size=(dp(18), dp(18)),
                    size_hint=(None, None)
                )
                card.add_widget(card.checkmark)

            # Bind position, size updates, and touch events
            card.bind(
                pos=self._update_card_canvas,
                size=self._update_card_canvas,
                on_touch_down=self._on_card_touch_down,
                on_touch_up=self._on_card_touch_up
            )
            card.note_data = note
            card.is_selected = False

            # Title
            title_label = Label(
                text=note['title'],
                size_hint=(1, None),
                height=dp(28),
                color=get_color_from_hex(self.colors[self.theme]['text']),
                font_size=dp(15),
                font_name='Arial',
                bold=True,
                halign='left',
                valign='top',
                text_size=(card_width - dp(24), dp(28))
            )

            # Note content
            content_label = Label(
                text=note['content'],
                size_hint=(1, 1),
                halign='left',
                valign='top',
                font_size=dp(13),
                font_name='Arial',
                color=get_color_from_hex(self.colors[self.theme]['text'] + 'CC'),
                text_size=(card_width - dp(24), None),
                shorten=True,
                max_lines=4
            )

            # Footer with date only
            footer = BoxLayout(size_hint=(1, None), height=dp(32), spacing=dp(8))

            date_label = Label(
                text=note['date'].split()[0],
                size_hint=(1, 1),
                halign='left',
                valign='middle',
                font_size=dp(12),
                font_name='Arial',
                color=get_color_from_hex(self.colors[self.theme]['text'] + '80'),
                text_size=(card_width - dp(24), dp(32))
            )

            footer.add_widget(date_label)

            card.add_widget(title_label)
            card.add_widget(content_label)
            card.add_widget(footer)

            self.notes_grid.add_widget(card)

    def _update_card_canvas(self, instance, _):
        """Update canvas elements when card position or size changes"""
        card_width = instance.width
        instance.shadow.pos = (instance.x + dp(2), instance.y - dp(2))
        instance.shadow.size = (card_width, dp(180))
        instance.bg.pos = instance.pos
        instance.bg.size = (card_width, dp(180))
        instance.border.rounded_rectangle = (instance.x, instance.y, card_width, dp(180), dp(12))
        instance.checkmark_bg.pos = (instance.x + card_width - dp(32), instance.y + instance.height - dp(32))
        instance.checkmark.pos = (instance.x + card_width - dp(32) + dp(5), instance.y + instance.height - dp(32) + dp(3))

    def _on_card_touch_down(self, instance, touch):
        """Handle touch down on the card"""
        if instance.collide_point(*touch.pos):
            self.touch_start_time = touch.time_start
            return True
        return False

    def _on_card_touch_up(self, instance, touch):
        """Handle touch up on the card"""
        if instance.collide_point(*touch.pos):
            touch_duration = touch.time_end - self.touch_start_time

            if touch_duration >= 0.5:
                self.is_selection_mode = True
                self._toggle_card_selection(instance)
            else:
                if self.is_selection_mode:
                    self._toggle_card_selection(instance)
                else:
                    self._on_note_pressed(instance)
            return True
        return False

    def _toggle_card_selection(self, card):
        """Toggle the selection state of a card"""
        card.is_selected = not card.is_selected
        if card.is_selected:
            self.selected_cards.add(card)
            # Добавляем только галочку
            card.checkmark.text = '✔'
            card.checkmark.font_name = 'fonts/NotoEmoji-VariableFont_wght.ttf'
            card.checkmark.color = (0.2, 0.8, 0.2, 1)  # Зелёный цвет самой галочки
            # Устанавливаем позицию галочки в правом верхнем углу
            card.checkmark.pos = (card.x + card.width - dp(32), card.y + card.height - dp(32))
        else:
            self.selected_cards.remove(card) if card in self.selected_cards else None
            card.checkmark.text = ''  # Убираем галочку

        # Обновляем интерфейс
        card.canvas.ask_update()

        if self.selected_cards:
            self._show_delete_panel()
        else:
            self._hide_delete_panel()
            self.is_selection_mode = False

    def _show_delete_panel(self):
        """Show the delete panel with a trash icon"""
        if self.delete_panel:
            self.root_layout.remove_widget(self.delete_panel)

        self.delete_panel = BoxLayout(
            size_hint=(1, None),
            height=dp(60),
            pos_hint={'bottom': 0},
            padding=dp(10),
            spacing=dp(10)
        )

        # Создаем контейнер для круглой кнопки
        btn_container = FloatLayout(
            size_hint=(None, None),
            size=(dp(56), dp(56))
        )

        # Черный круглый фон
        with btn_container.canvas.before:
            Color(0, 0, 0, 1)  # Черный цвет
            btn_container.bg_circle = Ellipse(
                pos=btn_container.pos,
                size=btn_container.size
            )

        # Прозрачная кнопка с иконкой
        delete_btn = Button(
            text='🗑️',
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            background_normal='',
            background_color=(0, 0, 0, 0),  # Полностью прозрачная
            color=(1, 1, 1, 1),  # Белый цвет иконки
            font_size=dp(24),
            font_name='fonts/NotoEmoji-VariableFont_wght.ttf',
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # Обновляем позицию фона при изменении позиции контейнера
        btn_container.bind(
            pos=lambda inst, pos: setattr(inst.bg_circle, 'pos', pos),
            size=lambda inst, size: setattr(inst.bg_circle, 'size', size)
        )

        delete_btn.bind(on_press=self._delete_selected_notes)
        btn_container.add_widget(delete_btn)
        self.delete_panel.add_widget(btn_container)
        self.root_layout.add_widget(self.delete_panel)

    def _hide_delete_panel(self):
        """Hide the delete panel"""
        if self.delete_panel:
            self.root_layout.remove_widget(self.delete_panel)
            self.delete_panel = None

    def _delete_selected_notes(self, _):
        """Delete all selected notes"""
        # Создаем копию множества для безопасного удаления
        for card in list(self.selected_cards):
            try:
                if card.note_data in self.notes:
                    self.notes.remove(card.note_data)
            except ValueError:
                continue

        self.selected_cards.clear()
        self.is_selection_mode = False
        self._hide_delete_panel()
        self.save_data()
        self.header_label.text = f"Заметки\n{len(self.notes)} заметок"
        self._update_note_cards(self.notes_grid, self.notes_grid.width)

    def _on_note_pressed(self, instance):
        """Handle note press"""
        if hasattr(instance, 'note_data'):
            self.current_note = instance.note_data
            self.show_editor()

    def show_editor(self, _=None):
        """Shows note editor"""
        self.root_layout.clear_widgets()

        editor_layout = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))

        # Back button
        back_btn = Button(
            text='← Назад',
            size_hint=(1, None),
            height=dp(48),
            background_normal='',
            background_color=get_color_from_hex(self.colors[self.theme]['primary']),
            color=(1, 1, 1, 1),
            font_size=dp(14),
            font_name='Arial',
            bold=True
        )
        back_btn.bind(on_press=self.back_to_list)

        # Editor fields
        self.editor_title = TextInput(
            text=self.current_note['title'] if self.current_note else '',
            hint_text='Заголовок заметки',
            size_hint=(1, None),
            height=dp(48),
            font_size=dp(16),
            font_name='Arial',
            padding=(dp(12), dp(8)),
            background_normal='',
            background_color=get_color_from_hex(self.colors[self.theme]['card']),
            foreground_color=get_color_from_hex(self.colors[self.theme]['text']),
            hint_text_color=get_color_from_hex(self.colors[self.theme]['text'] + '80'),
            multiline=False
        )

        self.editor_content = TextInput(
            text=self.current_note['content'] if self.current_note else '',
            hint_text='Введите текст заметки...',
            size_hint=(1, 1),
            font_size=dp(14),
            font_name='Arial',
            padding=(dp(12), dp(8)),
            background_normal='',
            background_color=get_color_from_hex(self.colors[self.theme]['card']),
            foreground_color=get_color_from_hex(self.colors[self.theme]['text']),
            hint_text_color=get_color_from_hex(self.colors[self.theme]['text'] + '80')
        )

        # Save button
        save_btn = Button(
            text='Сохранить',
            size_hint=(1, None),
            height=dp(48),
            background_normal='',
            background_color=get_color_from_hex(self.colors[self.theme]['primary']),
            color=(1, 1, 1, 1),
            font_size=dp(14),
            font_name='Arial',
            bold=True
        )
        save_btn.bind(on_press=lambda _: self.save_note())

        editor_layout.add_widget(back_btn)
        editor_layout.add_widget(self.editor_title)
        editor_layout.add_widget(self.editor_content)
        editor_layout.add_widget(save_btn)

        self.root_layout.add_widget(editor_layout)

    def save_note(self):
        """Saves note"""
        title = self.editor_title.text.strip()
        content = self.editor_content.text.strip()

        if not title:
            return

        note_data = {
            'title': title,
            'content': content,
            'date': datetime.now().strftime("%d.%m.%Y %H:%M")
        }

        if self.current_note:
            index = self.notes.index(self.current_note)
            self.notes[index] = note_data
        else:
            self.notes.append(note_data)

        self.save_data()
        self.back_to_list()

    def back_to_list(self, _=None):
        """Return to notes list"""
        self.current_note = None
        self.root_layout.clear_widgets()
        self.root_layout.add_widget(self.main_layout)
        self.root_layout.add_widget(self.add_btn)
        self.header_label.text = f"Заметки\n{len(self.notes)} заметок"
        self._update_note_cards(self.notes_grid, self.notes_grid.width)

    def update_theme(self):
        """Updates color theme"""
        colors = self.colors[self.theme]
        Window.clearcolor = get_color_from_hex(colors['bg'])

        self.header.canvas.before.clear()
        with self.header.canvas.before:
            Color(*get_color_from_hex(colors['header']))
            self.header.bg = Rectangle(pos=self.header.pos, size=self.header.size)
        self.header.bind(pos=self._update_header_canvas, size=self._update_header_canvas)

        self.header_label.color = get_color_from_hex(colors['text'])
        self._update_note_cards(self.notes_grid, self.notes_grid.width)

    def _update_header_canvas(self, instance, _):
        """Update header canvas when position or size changes"""
        instance.bg.pos = instance.pos
        instance.bg.size = instance.size

    def save_data(self):
        """Saves data to file"""
        data = {'notes': self.notes}
        try:
            with open('notes_data.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def load_data(self):
        """Loads data from file"""
        try:
            if os.path.exists('notes_data.json'):
                with open('notes_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = data.get('notes', [])
        except Exception as e:
            self.notes = []


if __name__ == '__main__':
    SamsungNotesApp().run()