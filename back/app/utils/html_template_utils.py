def replace_error_template_vars(html_content: str, title: str, message: str) -> str:
    return html_content.replace("{{ title }}", title).replace("{{ message }}", message)


def replace_success_template_vars(html_content: str, message: str, user_name: str) -> str:
    return html_content.replace("{{ message }}", message).replace("{{ user_name }}", user_name)
