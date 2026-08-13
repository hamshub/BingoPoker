"""ColorPalette - Manages color assignment for room users.

Provides a 10-color palette with rolling assignment logic to ensure
each user in a room gets a unique color for identification.
"""


class ColorPalette:
    """Manages color assignment and availability for room users."""

    # 10 maximally contrasted colors spanning the hue wheel
    COLORS = [
        "#E63946",      # 1. Red
        "#F4A300",      # 2. Amber
        "#2EC4B6",      # 3. Teal
        "#A8DADC",      # 4. Ice Blue
        "#8338EC",      # 5. Violet
        "#06D6A0",      # 6. Mint Green
        "#FF6B35",      # 7. Orange
        "#3A86FF",      # 8. Royal Blue
        "#FF006E",      # 9. Hot Pink
        "#CBFF8C",      # 10. Lime
    ]

    @staticmethod
    def get_color_by_index(index: int) -> str:
        """Return color at position index, wrapping around if > 10 users."""
        return ColorPalette.COLORS[index % len(ColorPalette.COLORS)]
