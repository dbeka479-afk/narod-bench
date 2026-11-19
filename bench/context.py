from .views import ASSET_V


def assets(request):
    """Версия статики в ссылках (?v=…), чтобы браузер не держал старые скрипты после обновления."""
    return {"V": ASSET_V}
