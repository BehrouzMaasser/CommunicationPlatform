from django import template


register = template.Library()


@register.filter
def add_class(field, css_class):
    existing_classes = field.field.widget.attrs.get("class", "")

    classes = " ".join(
        value
        for value in [existing_classes, css_class]
        if value
    )

    return field.as_widget(
        attrs={
            **field.field.widget.attrs,
            "class": classes,
        }
    )
