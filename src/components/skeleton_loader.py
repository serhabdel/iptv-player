"""Skeleton loading components for improved perceived loading performance."""
import flet as ft
from typing import Optional


class SkeletonCard(ft.Container):
    """Animated skeleton placeholder for movie/series cards."""
    
    def __init__(
        self,
        width: int = 140,
        height: int = 200,
        title_lines: int = 2,
    ):
        super().__init__()
        
        # Shimmer animation using gradient
        self._shimmer_colors = ["#1a1a2e", "#2a2a3e", "#1a1a2e"]
        
        # Build skeleton content
        self.content = ft.Column(
            [
                # Image placeholder
                ft.Container(
                    width=width,
                    height=height,
                    border_radius=8,
                    bgcolor="#1a1a2e",
                    animate=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.center_left,
                        end=ft.alignment.center_right,
                        colors=self._shimmer_colors,
                    ),
                ),
                # Title placeholder lines
                ft.Column(
                    [
                        ft.Container(
                            width=width * (0.9 if i == 0 else 0.6),
                            height=12,
                            border_radius=4,
                            bgcolor="#1a1a2e",
                        )
                        for i in range(title_lines)
                    ],
                    spacing=4,
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.width = width + 16
        self.padding = 8
        self.animate_opacity = ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT)


class SkeletonListItem(ft.Container):
    """Animated skeleton placeholder for live TV list items."""
    
    def __init__(self):
        super().__init__()
        
        self.content = ft.Row(
            [
                # Logo placeholder
                ft.Container(
                    width=60,
                    height=40,
                    border_radius=6,
                    bgcolor="#1a1a2e",
                ),
                # Text placeholders
                ft.Column(
                    [
                        ft.Container(
                            width=200,
                            height=14,
                            border_radius=4,
                            bgcolor="#1a1a2e",
                        ),
                        ft.Container(
                            width=120,
                            height=12,
                            border_radius=4,
                            bgcolor="#1a1a2e",
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                # Favorite icon placeholder
                ft.Container(
                    width=24,
                    height=24,
                    border_radius=12,
                    bgcolor="#1a1a2e",
                ),
            ],
            spacing=16,
        )
        self.padding = ft.padding.symmetric(horizontal=16, vertical=12)
        self.border_radius = 8
        self.bgcolor = "#1a1a2e40"
        self.animate_opacity = ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT)


class SkeletonGrid(ft.Container):
    """Grid of skeleton cards for movie/series loading state."""
    
    def __init__(
        self,
        items_per_row: int = 5,
        rows: int = 2,
        card_width: int = 140,
        card_height: int = 200,
    ):
        super().__init__()
        
        rows_list = []
        for row_idx in range(rows):
            row_cards = []
            for col_idx in range(items_per_row):
                card = SkeletonCard(width=card_width, height=card_height)
                # Stagger opacity for shimmer effect
                card.opacity = 0.5 + (0.1 * ((row_idx + col_idx) % 5))
                row_cards.append(card)
            
            rows_list.append(
                ft.Row(
                    row_cards,
                    spacing=12,
                    wrap=True,
                )
            )
        
        self.content = ft.Column(
            rows_list,
            spacing=16,
        )
        self.expand = True


class SkeletonList(ft.Container):
    """List of skeleton items for live TV loading state."""
    
    def __init__(self, items: int = 10):
        super().__init__()
        
        list_items = []
        for i in range(items):
            item = SkeletonListItem()
            # Stagger opacity
            item.opacity = 0.5 + (0.05 * (i % 10))
            list_items.append(item)
        
        self.content = ft.Column(
            list_items,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )
        self.expand = True


class BufferingOverlay(ft.Container):
    """Overlay shown during video buffering."""
    
    def __init__(self):
        super().__init__()
        
        self._buffering_text = ft.Text(
            "Buffering...",
            color=ft.Colors.WHITE,
            size=14,
        )
        
        self._buffer_percent = ft.Text(
            "",
            color=ft.Colors.WHITE70,
            size=12,
        )
        
        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(
                        width=50,
                        height=50,
                        stroke_width=4,
                        color=ft.Colors.PURPLE_400,
                    ),
                    ft.Container(height=12),
                    self._buffering_text,
                    self._buffer_percent,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.BLACK),
            border_radius=16,
            padding=32,
        )
        
        self.visible = False
        self.expand = True
        self.alignment = ft.alignment.center
        self.animate_opacity = ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    
    def show(self, message: str = "Buffering..."):
        """Show the buffering overlay."""
        self._buffering_text.value = message
        self._buffer_percent.value = ""
        self.visible = True
        if self.page:
            self.update()
    
    def set_progress(self, percent: Optional[int] = None):
        """Update buffering progress."""
        if percent is not None:
            self._buffer_percent.value = f"{percent}%"
        else:
            self._buffer_percent.value = ""
        if self.page:
            self.update()
    
    def hide(self):
        """Hide the buffering overlay."""
        self.visible = False
        if self.page:
            self.update()


class ErrorOverlay(ft.Container):
    """Overlay shown when video playback fails with retry option."""
    
    def __init__(
        self,
        on_retry: Optional[callable] = None,
        on_back: Optional[callable] = None,
    ):
        super().__init__()
        
        self._on_retry = on_retry
        self._on_back = on_back
        
        self._error_message = ft.Text(
            "Failed to load stream",
            color=ft.Colors.WHITE,
            size=16,
            weight=ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER,
        )
        
        self._error_detail = ft.Text(
            "",
            color=ft.Colors.WHITE54,
            size=12,
            text_align=ft.TextAlign.CENTER,
        )
        
        self._retry_count = ft.Text(
            "",
            color=ft.Colors.WHITE38,
            size=11,
        )
        
        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE_ROUNDED,
                        color=ft.Colors.RED_400,
                        size=56,
                    ),
                    ft.Container(height=16),
                    self._error_message,
                    self._error_detail,
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                text="Go Back",
                                icon=ft.Icons.ARROW_BACK_ROUNDED,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE70,
                                    side=ft.BorderSide(1, ft.Colors.WHITE24),
                                ),
                                on_click=lambda e: self._on_back() if self._on_back else None,
                            ),
                            ft.ElevatedButton(
                                text="Retry",
                                icon=ft.Icons.REFRESH_ROUNDED,
                                bgcolor=ft.Colors.PURPLE_700,
                                color=ft.Colors.WHITE,
                                on_click=lambda e: self._on_retry() if self._on_retry else None,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                    ),
                    ft.Container(height=8),
                    self._retry_count,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.with_opacity(0.85, "#0a0a12"),
            border_radius=16,
            padding=40,
        )
        
        self.visible = False
        self.expand = True
        self.alignment = ft.alignment.center
        self.animate_opacity = ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    
    def show(self, message: str = "Failed to load stream", detail: str = "", retry_attempt: int = 0):
        """Show the error overlay."""
        self._error_message.value = message
        self._error_detail.value = detail
        if retry_attempt > 0:
            self._retry_count.value = f"Retry attempt {retry_attempt}"
        else:
            self._retry_count.value = ""
        self.visible = True
        if self.page:
            self.update()
    
    def hide(self):
        """Hide the error overlay."""
        self.visible = False
        if self.page:
            self.update()
