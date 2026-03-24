import winreg


def create_test_data():
    source_path = r"Software\Lab4Source"

    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, source_path)
    winreg.SetValueEx(key, "UserName", 0, winreg.REG_SZ, "Roman")
    winreg.SetValueEx(key, "Age", 0, winreg.REG_DWORD, 25)
    winreg.CloseKey(key)

    settings_path = r"Software\Lab4Source\Settings"
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, settings_path)
    winreg.SetValueEx(key, "Theme", 0, winreg.REG_SZ, "Dark")
    winreg.SetValueEx(key, "FontSize", 0, winreg.REG_DWORD, 14)
    winreg.CloseKey(key)

    profile_path = r"Software\Lab4Source\Profile"
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, profile_path)
    winreg.SetValueEx(key, "City", 0, winreg.REG_SZ, "Astana")
    winreg.SetValueEx(key, "Course", 0, winreg.REG_DWORD, 2)
    winreg.CloseKey(key)


def copy_values(source_key, dest_key):
    index = 0
    while True:
        try:
            name, value, reg_type = winreg.EnumValue(source_key, index)
            if reg_type in (winreg.REG_SZ, winreg.REG_DWORD):
                winreg.SetValueEx(dest_key, name, 0, reg_type, value)
            index += 1
        except OSError:
            break


def copy_key_recursive(source_root, source_path, dest_root, dest_path):
    source_key = winreg.OpenKey(source_root, source_path, 0, winreg.KEY_READ)
    dest_key = winreg.CreateKey(dest_root, dest_path)

    copy_values(source_key, dest_key)

    index = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(source_key, index)
            source_subpath = source_path + "\\" + subkey_name
            dest_subpath = dest_path + "\\" + subkey_name
            copy_key_recursive(source_root, source_subpath, dest_root, dest_subpath)
            index += 1
        except OSError:
            break

    winreg.CloseKey(source_key)
    winreg.CloseKey(dest_key)


def main():
    source_path = r"Software\Lab4Source"
    dest_path = r"Software\Lab4Copy"

    try:
        print("Создание тестовых данных...")
        create_test_data()

        print("Копирование раздела реестра...")
        copy_key_recursive(
            winreg.HKEY_CURRENT_USER, source_path, winreg.HKEY_CURRENT_USER, dest_path
        )

        print("Копирование успешно завершено.")
    except Exception as e:
        print("Ошибка:", e)

    input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
