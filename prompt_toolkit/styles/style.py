"""
Tool for creating styles from a dictionary.
"""
from __future__ import unicode_literals, absolute_import
import itertools
from .base import BaseStyle, DEFAULT_ATTRS, ANSI_COLOR_NAMES, Attrs

__all__ = (
    'Style',
)


def _colorformat(text):
    """
    Parse/validate color format.

    Like in Pygments, but also support the ANSI color names.
    (These will map to the colors of the 16 color palette.)
    """
    if text[0:1] == '#':
        col = text[1:]
        if col in ANSI_COLOR_NAMES:
            return col
        elif len(col) == 6:
            return col
        elif len(col) == 3:
            return col[0]*2 + col[1]*2 + col[2]*2
    elif text in ('', 'default'):
        return text

    raise ValueError('Wrong color format %r' % text)


# Attributes, when they are not filled in by a style. None means that we take
# the value from the parent.
_EMPTY_ATTRS = Attrs(color=None, bgcolor=None, bold=None, underline=None,
                     italic=None, blink=None, reverse=None)

def _parse_style_str(style_str, style=None):
    """
    Take a style string, e.g.  'bg:red #88ff00 class:title'
    and return a (`Attrs`, class_names) tuple.
    """
    class_names = []

    # Start from default Attrs.
    if 'noinherit' in style_str:
        attrs = DEFAULT_ATTRS
    else:
        attrs = _EMPTY_ATTRS

    # Now update with the given attributes.
    for part in style_str.split():
        if part == 'noinherit':
            pass
        elif part == 'bold':
            attrs = attrs._replace(bold=True)
        elif part == 'nobold':
            attrs = attrs._replace(bold=False)
        elif part == 'italic':
            attrs = attrs._replace(italic=True)
        elif part == 'noitalic':
            attrs = attrs._replace(italic=False)
        elif part == 'underline':
            attrs = attrs._replace(underline=True)
        elif part == 'nounderline':
            attrs = attrs._replace(underline=False)

        # prompt_toolkit extensions. Not in Pygments.
        elif part == 'blink':
            attrs = attrs._replace(blink=True)
        elif part == 'noblink':
            attrs = attrs._replace(blink=False)
        elif part == 'reverse':
            attrs = attrs._replace(reverse=True)
        elif part == 'noreverse':
            attrs = attrs._replace(reverse=False)

        # Pygments properties that we ignore.
        elif part in ('roman', 'sans', 'mono'):
            pass
        elif part.startswith('border:'):
            pass

        # Inclusion of class names.
        elif part.startswith('class:'):
            class_names.extend(part[6:].lower().split(','))

        # Ignore pieces in between square brackets. This is internal stuff.
        # Like '[transparant]' or '[set-cursor-position]'.
        elif part.startswith('[') and part.endswith(']'):
            pass

        # Colors.
        elif part.startswith('bg:'):
            attrs = attrs._replace(bgcolor=_colorformat(part[3:]))
        else:
            attrs = attrs._replace(color=_colorformat(part))

    return attrs, class_names


class Style(BaseStyle):
    """
    Create a ``Style`` instance from a list of style rules.

    The `style_rules` is supposed to be a list of ('classnames', 'style') tuples.
    The classnames are a whitespace separated string of class names and the
    style string is just like a Pygments style definition, but with a few
    additions: it supports 'reverse' and 'blink'.

    Usage::

        Style([
            ('title', '#ff0000 bold underline'),
            ('something-else', 'reverse'),
            ('class1 class2', 'reverse'),
        ])

    The ``from_dict`` classmethod is similar, but takes a dictionary as input.
    """
    def __init__(self, style_rules):
        assert isinstance(style_rules, list)

        class_names_and_attrs = []

        # Loop through the rules in the order they were defined.
        # Rules that are defined later get priority.
        for class_names, style_str in style_rules:
            # The order of the class names doesn't matter.
            class_names = tuple(sorted(class_names.lower().split()))

            attrs, class_names_2 = _parse_style_str(style_str, style=None)
            assert not class_names_2

            class_names_and_attrs.append((class_names, attrs))

        self.class_names_and_attrs = class_names_and_attrs

    @classmethod
    def from_dict(cls, style_dict):
        """
        :param include_defaults: Include the defaults (built-in) styling for
            selected text, etc...)
        """
        return cls(list(style_dict.items()))

    def get_attrs_for_style_str(self, style_str, default=DEFAULT_ATTRS):
        """
        Get `Attrs` for the given style string.
        """
        # Parse style string.
        inline_attrs, class_names = _parse_style_str(style_str, style=None)

        # Build a set of all possible class combinations.
        combos = set()
        combos.add(('', ))  # Add the default.

        for count in range(1, len(class_names) + 1):
            for combo in itertools.combinations(class_names, count):
                combos.add(combo)

        # Get list of Attrs, according to matches in our Style.
        list_of_attrs = [default]

        # Loop through the list of styles that apply.
        for class_names, attr in self.class_names_and_attrs:
            if class_names in combos:
                list_of_attrs.append(attr)

        # Add the inline style.
        list_of_attrs.append(inline_attrs)

        return _merge_attrs(list_of_attrs)

    def invalidation_hash(self):
        return id(self.class_names_and_attrs)


def _merge_attrs(list_of_attrs):
    """
    Take a list of :class:`.Attrs` instances and merge them into one.
    Every `Attr` in the list can override the styling of the previous one. So,
    the last one has highest priority.
    """
    def _or(*values):
        " Take first not-None value, starting at the end. "
        for v in values[::-1]:
            if v is not None:
                return v

    return Attrs(
        color=_or('', *[a.color for a in list_of_attrs]),
        bgcolor=_or('', *[a.bgcolor for a in list_of_attrs]),
        bold=_or(False, *[a.bold for a in list_of_attrs]),
        underline=_or(False, *[a.underline for a in list_of_attrs]),
        italic=_or(False, *[a.italic for a in list_of_attrs]),
        blink=_or(False, *[a.blink for a in list_of_attrs]),
        reverse=_or(False, *[a.reverse for a in list_of_attrs]))