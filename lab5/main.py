import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Dict, List, Optional, Set, cast

import psutil
import win32con
import win32gui
import win32ui
from PIL import Image, ImageTk


@dataclass
class ProcessRecord:
    pid: int
    name: str
    exe: str
    username: str


class ProcessViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Просмотр процессов")
        self.root.geometry("1380x780")
        self.root.minsize(1100, 680)
        self.root.state("zoomed")
        self.root.configure(bg="#eef3f8")

        self.process_records: List[ProcessRecord] = []
        self.module_icons: Dict[str, Optional[ImageTk.PhotoImage]] = {}

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Готово к работе")
        self.summary_var = tk.StringVar(value="Процессы не загружены")
        self.selected_name_var = tk.StringVar(value="Не выбран")
        self.selected_pid_var = tk.StringVar(value="-")
        self.selected_user_var = tk.StringVar(value="-")
        self.selected_path_var = tk.StringVar(value="-")

        self._configure_styles()
        self._build_ui()
        self.search_var.trace_add("write", self._on_search_changed)
        self.refresh_processes()

    def _configure_styles(self):
        style = ttk.Style(self.root)

        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        self.root.option_add("*Font", ("Segoe UI", 10))

        style.configure("App.TFrame", background="#eef3f8")
        style.configure(
            "Panel.TLabelframe",
            background="#eef3f8",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Panel.TLabelframe.Label",
            background="#eef3f8",
            foreground="#1f2a37",
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Header.TLabel",
            background="#eef3f8",
            foreground="#11263c",
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Muted.TLabel",
            background="#eef3f8",
            foreground="#5d6b7a",
            font=("Segoe UI", 10),
        )
        style.configure(
            "InfoTitle.TLabel",
            background="#eef3f8",
            foreground="#5d6b7a",
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "InfoValue.TLabel",
            background="#eef3f8",
            foreground="#1f2a37",
            font=("Segoe UI", 10),
        )
        style.configure("Accent.TButton", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_ui(self):
        root_frame = ttk.Frame(self.root, padding=14, style="App.TFrame")
        root_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(root_frame, style="App.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(
            header_frame,
            text="Монитор процессов Windows",
            style="Header.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Список процессов, сведения о выбранном процессе и модули, загруженные в его адресное пространство.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        toolbar = ttk.Frame(root_frame, padding=(12, 10), style="App.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            toolbar,
            text="Обновить процессы",
            style="Accent.TButton",
            command=self.refresh_processes,
        ).pack(side=tk.LEFT)
        ttk.Button(
            toolbar,
            text="Обновить модули",
            style="Accent.TButton",
            command=self.refresh_modules_for_selected,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            toolbar,
            text="Поиск:",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(20, 8))
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=34)
        search_entry.pack(side=tk.LEFT)

        ttk.Label(
            toolbar,
            textvariable=self.summary_var,
            style="Muted.TLabel",
        ).pack(side=tk.RIGHT)

        content = ttk.PanedWindow(root_frame, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.LabelFrame(
            content,
            text="Процессы",
            padding=10,
            style="Panel.TLabelframe",
        )
        right_panel = ttk.LabelFrame(
            content,
            text="Модули процесса",
            padding=10,
            style="Panel.TLabelframe",
        )
        content.add(left_panel, weight=5)
        content.add(right_panel, weight=7)

        self.process_tree = ttk.Treeview(
            left_panel,
            columns=("pid", "user", "exe"),
            show="tree headings",
            selectmode="browse",
        )
        self.process_tree.heading("#0", text="Процесс")
        self.process_tree.heading("pid", text="PID")
        self.process_tree.heading("user", text="Пользователь")
        self.process_tree.heading("exe", text="Исполняемый файл")
        self.process_tree.column("#0", width=220, minwidth=180)
        self.process_tree.column("pid", width=80, anchor=tk.CENTER, minwidth=70)
        self.process_tree.column("user", width=180, minwidth=140)
        self.process_tree.column("exe", width=420, minwidth=260)

        process_scroll_y = ttk.Scrollbar(
            left_panel, orient=tk.VERTICAL, command=self.process_tree.yview
        )
        process_scroll_x = ttk.Scrollbar(
            left_panel, orient=tk.HORIZONTAL, command=self.process_tree.xview
        )
        self.process_tree.configure(
            yscrollcommand=process_scroll_y.set,
            xscrollcommand=process_scroll_x.set,
        )

        self.process_tree.grid(row=0, column=0, sticky="nsew")
        process_scroll_y.grid(row=0, column=1, sticky="ns")
        process_scroll_x.grid(row=1, column=0, sticky="ew")

        details_frame = ttk.Frame(left_panel, style="App.TFrame", padding=(0, 12, 0, 0))
        details_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        details_frame.columnconfigure(1, weight=1)

        detail_rows = [
            ("Имя процесса", self.selected_name_var),
            ("PID", self.selected_pid_var),
            ("Пользователь", self.selected_user_var),
            ("Путь", self.selected_path_var),
        ]
        for row_index, (title, variable) in enumerate(detail_rows):
            ttk.Label(details_frame, text=title, style="InfoTitle.TLabel").grid(
                row=row_index, column=0, sticky="nw", padx=(0, 12), pady=2
            )
            ttk.Label(
                details_frame,
                textvariable=variable,
                style="InfoValue.TLabel",
                wraplength=420,
                justify=tk.LEFT,
            ).grid(row=row_index, column=1, sticky="ew", pady=2)

        left_panel.rowconfigure(0, weight=1)
        left_panel.columnconfigure(0, weight=1)

        self.module_tree = ttk.Treeview(
            right_panel,
            columns=("path",),
            show="tree headings",
            selectmode="browse",
        )
        self.module_tree.heading("#0", text="Модуль")
        self.module_tree.heading("path", text="Полный путь")
        self.module_tree.column("#0", width=240, minwidth=180)
        self.module_tree.column("path", width=620, minwidth=320)

        module_scroll_y = ttk.Scrollbar(
            right_panel, orient=tk.VERTICAL, command=self.module_tree.yview
        )
        module_scroll_x = ttk.Scrollbar(
            right_panel, orient=tk.HORIZONTAL, command=self.module_tree.xview
        )
        self.module_tree.configure(
            yscrollcommand=module_scroll_y.set,
            xscrollcommand=module_scroll_x.set,
        )

        self.module_tree.grid(row=0, column=0, sticky="nsew")
        module_scroll_y.grid(row=0, column=1, sticky="ns")
        module_scroll_x.grid(row=1, column=0, sticky="ew")

        right_panel.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)

        self.process_tree.bind("<<TreeviewSelect>>", self.on_process_select)

        status_bar = ttk.Label(
            root_frame,
            textvariable=self.status_var,
            style="Muted.TLabel",
            anchor="w",
            padding=(4, 8, 4, 0),
        )
        status_bar.pack(fill=tk.X)

    def set_status(self, text: str):
        self.status_var.set(text)

    def refresh_processes(self):
        current_selection = self.process_tree.selection()
        selected_pid = int(current_selection[0]) if current_selection else None

        self.process_records.clear()
        self.process_tree.delete(*self.process_tree.get_children())
        self.module_tree.delete(*self.module_tree.get_children())
        self._reset_selected_details()

        for proc in psutil.process_iter(["pid", "name", "exe", "username"]):
            try:
                info = proc.info
                self.process_records.append(
                    ProcessRecord(
                        pid=info["pid"],
                        name=info.get("name") or "Без имени",
                        exe=info.get("exe") or "",
                        username=info.get("username") or "Недоступно",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.process_records.sort(key=lambda item: (item.name.lower(), item.pid))
        self._populate_process_tree(selected_pid=selected_pid)
        self.set_status(
            f"Список процессов обновлен: {len(self.process_records)} записей"
        )

    def _populate_process_tree(self, selected_pid: Optional[int] = None):
        query = self.search_var.get().strip().lower()
        visible_count = 0
        matched_selection = False

        self.process_tree.delete(*self.process_tree.get_children())

        for record in self.process_records:
            searchable = (
                f"{record.name} {record.pid} {record.exe} {record.username}".lower()
            )
            if query and query not in searchable:
                continue

            icon = self.get_file_icon(record.exe)
            insert_kwargs = {
                "iid": str(record.pid),
                "text": record.name,
                "values": (record.pid, record.username, record.exe or "Недоступно"),
            }
            if icon is not None:
                insert_kwargs["image"] = icon

            self.process_tree.insert("", tk.END, **insert_kwargs)
            visible_count += 1

            if selected_pid == record.pid:
                self.process_tree.selection_set(str(record.pid))
                self.process_tree.focus(str(record.pid))
                self.process_tree.see(str(record.pid))
                matched_selection = True

        self.summary_var.set(
            f"Показано: {visible_count} из {len(self.process_records)} процессов"
        )

        if matched_selection:
            self.refresh_modules_for_selected()
        else:
            self.module_tree.delete(*self.module_tree.get_children())
            self._reset_selected_details()

    def _on_search_changed(self, *_args):
        current_selection = self.process_tree.selection()
        selected_pid = int(current_selection[0]) if current_selection else None
        self._populate_process_tree(selected_pid=selected_pid)

    def _reset_selected_details(self):
        self.selected_name_var.set("Не выбран")
        self.selected_pid_var.set("-")
        self.selected_user_var.set("-")
        self.selected_path_var.set("-")

    def on_process_select(self, _event=None):
        self.refresh_modules_for_selected()

    def refresh_modules_for_selected(self):
        selection = self.process_tree.selection()
        self.module_tree.delete(*self.module_tree.get_children())

        if not selection:
            self._reset_selected_details()
            self.set_status("Выберите процесс, чтобы увидеть его модули")
            return

        pid = int(selection[0])

        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
            process_user = self._safe_call(proc.username, default="Недоступно")
            process_path = self._safe_call(proc.exe, default="Недоступно")

            self.selected_name_var.set(process_name or "Без имени")
            self.selected_pid_var.set(str(pid))
            self.selected_user_var.set(process_user)
            self.selected_path_var.set(process_path)

            module_paths = self._collect_module_paths(proc, process_path)
            for path in module_paths:
                module_name = os.path.basename(path) or path
                icon = self.get_file_icon(path)
                insert_kwargs = {
                    "text": module_name,
                    "values": (path,),
                }
                if icon is not None:
                    insert_kwargs["image"] = icon

                self.module_tree.insert("", tk.END, **insert_kwargs)

            self.set_status(f"PID {pid}: найдено модулей {len(module_paths)}")
        except psutil.NoSuchProcess:
            self._reset_selected_details()
            self.set_status("Процесс уже завершился")
        except psutil.AccessDenied:
            self._reset_selected_details()
            self.set_status("Недостаточно прав для чтения процесса")
        except Exception as error:
            self._reset_selected_details()
            self.set_status(f"Не удалось загрузить модули: {error}")

    def _collect_module_paths(
        self, proc: psutil.Process, process_path: str
    ) -> List[str]:
        module_paths: List[str] = []
        seen: Set[str] = set()

        if (
            process_path
            and process_path != "Недоступно"
            and os.path.isabs(process_path)
        ):
            seen.add(process_path)
            module_paths.append(process_path)

        try:
            for mapped_file in proc.memory_maps():
                path = getattr(mapped_file, "path", "")
                if not path or not os.path.isabs(path) or path in seen:
                    continue
                seen.add(path)
                module_paths.append(path)
        except (psutil.AccessDenied, psutil.NoSuchProcess, NotImplementedError):
            pass

        module_paths.sort(key=lambda item: os.path.basename(item).lower())
        return module_paths

    def _safe_call(self, func, default: str) -> str:
        try:
            value = func()
            return value or default
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            return default

    def get_file_icon(self, file_path: str):
        if not file_path:
            return None

        if file_path in self.module_icons:
            return self.module_icons[file_path]

        if not os.path.exists(file_path):
            self.module_icons[file_path] = None
            return None

        large_icons: List[Any] = []
        small_icons: List[Any] = []
        desktop_handle_raw: Optional[int] = None
        screen_dc_raw: Optional[Any] = None
        memory_dc_raw: Optional[Any] = None
        bitmap_raw: Optional[Any] = None

        try:
            large_icons, small_icons = win32gui.ExtractIconEx(file_path, 0)
            icon_handle = (
                small_icons[0]
                if small_icons
                else (large_icons[0] if large_icons else None)
            )
            if not icon_handle:
                self.module_icons[file_path] = None
                return None

            desktop_handle_raw = int(win32gui.GetDC(0))
            screen_dc_raw = win32ui.CreateDCFromHandle(desktop_handle_raw)
            if screen_dc_raw is None:
                self.module_icons[file_path] = None
                return None

            memory_dc_raw = screen_dc_raw.CreateCompatibleDC()
            if memory_dc_raw is None:
                self.module_icons[file_path] = None
                return None

            bitmap_raw = win32ui.CreateBitmap()
            if bitmap_raw is None:
                self.module_icons[file_path] = None
                return None

            screen_dc = cast(Any, screen_dc_raw)
            memory_dc = cast(Any, memory_dc_raw)
            bitmap = cast(Any, bitmap_raw)

            bitmap.CreateCompatibleBitmap(screen_dc, 16, 16)
            memory_dc.SelectObject(bitmap)

            rect = cast(Any, (0, 0, 16, 16))
            brush = cast(Any, win32gui.GetStockObject(win32con.WHITE_BRUSH))
            win32gui.FillRect(
                memory_dc.GetSafeHdc(),
                rect,
                brush,
            )
            win32gui.DrawIconEx(
                memory_dc.GetSafeHdc(),
                0,
                0,
                icon_handle,
                16,
                16,
                0,
                cast(Any, 0),
                win32con.DI_NORMAL,
            )

            bitmap_info = bitmap.GetInfo()
            bitmap_bytes = bitmap.GetBitmapBits(True)
            image = Image.frombuffer(
                "RGBA",
                (bitmap_info["bmWidth"], bitmap_info["bmHeight"]),
                bitmap_bytes,
                "raw",
                "BGRA",
                0,
                1,
            ).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            photo = ImageTk.PhotoImage(image)

            self.module_icons[file_path] = photo
            return photo
        except Exception:
            self.module_icons[file_path] = None
            return None
        finally:
            if large_icons:
                for handle in large_icons:
                    win32gui.DestroyIcon(handle)
            if small_icons:
                for handle in small_icons:
                    win32gui.DestroyIcon(handle)
            if memory_dc_raw is not None:
                memory_dc_raw.DeleteDC()
            if screen_dc_raw is not None:
                screen_dc_raw.DeleteDC()
            if desktop_handle_raw is not None:
                win32gui.ReleaseDC(0, desktop_handle_raw)
            if bitmap_raw is not None:
                win32gui.DeleteObject(bitmap_raw.GetHandle())


def main():
    root = tk.Tk()
    ProcessViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
