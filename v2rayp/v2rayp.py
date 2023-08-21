import io
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from contextlib import redirect_stdout

import psutil
import pyperclip
import PySimpleGUI as psg
from __version__ import __version__
from libs.ConnectGost import ConnectGost
from libs.ConnectV2Ray import ConnectV2Ray
from libs.ExportURLfromConfig import ExportURLfromConfig
from libs.GFW_Interface import GFW_Interface
from libs.GUIs.FileBrowser import FileBrowser
from libs.GUIs.GostGUI import GostGUI
from libs.GUIs.SettingGUI import SettingGUI
from libs.GUIs.TrojanGUI import TrojanGUI
from libs.GUIs.VlessGUI import VlessGUI
from libs.GUIs.VmessGUI import VmessGUI
from libs.in_win import (
    FactorySetting,
    config_path,
    download_xray_gost,
    inside_windows,
    pass_by_ref,
)
from libs.NetTools import NetTools
from libs.QRCode import QRCode
from libs.RefereshEditPage import RefereshEditPage
from libs.RefereshTableContent import RefereshTableContent
from libs.SaveGUIConfigPage import SaveGUIConfigPage
from libs.Subscriptions import Subscriptions
from libs.V2RayURL2Config import generateConfig

# sys.path.append("v2rayp")


# sys.path.append(
#     "libs"
# )  # add to settings.json -> "python.analysis.extraPaths": [ "libs"  ],"python.linting.pylintArgs": [ "--init-hook", "import sys; sys.path.append('libs')"]


if inside_windows():
    from psgtray import SystemTray


current_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(current_dir)
width = 1000


psg.theme("DarkGrey5")
# psg.set_options(font=("Arial Bold", 10))
psg.set_options(font=("", 12))
print(config_path())


class MainGUI:
    # _stdout_main = None
    enable_debug_terminal = None

    def __init__(self) -> None:
        self._stdout_main = sys.stdout
        # self.copy_config_folder()
        self.selected_profile_number = 0
        self._read_gui_config()
        self._generate_layout()
        self.mline_text = ""
        self.connectv2ray = None
        self.GFW_port = 2500
        self.gfw_interface = None
        self.thrd_check_connection = False
        self.thread_exit = None
        self.first_minimized = True
        self.settings: dict = None
        self.isHide = False
        self.show = True
        self.referesh_terminal_period = 0.5
        self.thrd_check_connection = None
        threading.Thread(target=self._update_debug, daemon=True).start()

    @staticmethod
    def copy_config_folder():
        if inside_windows():
            os.popen(f"mkdir {config_path()}").read()
            out = os.popen("dir").read()
            if "configs" in out:
                cmd = f"Xcopy /E /I /Y configs {config_path()}"
                res = os.popen(cmd).read()
        else:
            os.popen(f"mkdir -p {config_path()}").read()
            out = os.popen(f"ls {current_dir}").read()
            print("config path:", config_path())
            print(current_dir)
            if "configs" in out:
                cmd = f"cp -R {current_dir}/configs/* {config_path()}/"
                # print(cmd)
                res = os.popen(cmd).read()
                print(res)

    def _generate_layout(self):
        self.layout = [
            [self.generate_menu()],
            [self.generate_top_part()],
            [self.generate_middle_part()],
            [self.generate_Table()],
            [self.generate_ConsoleBox()],
            [[psg.ProgressBar(max_value=100, key="progressbar", size=(100, 10))]],
        ]

    def generate_middle_part(self):
        c1 = [
            psg.Text(
                "disconnected",
                key="connection_name",
                text_color="red",
                background_color="yellow",
            ),
        ]
        c2 = [
            psg.Input(
                default_text=self.gui_data["subscription"]
                if "subscription" in self.gui_data
                else "",
                key="subscription",
                size=(25),
            ),
            psg.Button("Update Subscription", key="update_subscription"),
            psg.Button("Delete Subscription", key="delete_subscription"),
        ]
        row = [
            [
                psg.Frame("Current Connction", [c1]),
                psg.Frame("Subscription", [c2]),
                psg.Frame(
                    "Shortcut",
                    [
                        [
                            psg.Button(
                                "Shortcut to Desktop",
                                font=(0, 8),
                                size=(10, 2),
                                key="shortcut",
                            ),
                        ]
                    ],
                ),
                psg.Frame(
                    "Exit",
                    [
                        [
                            psg.Button("Save", key="save"),
                            psg.Button("Exit", key="exit"),
                        ]
                    ],
                ),
            ],
        ]
        return row

    def _generate_tray(self):
        self.menu = [
            "OneClicked",
            [
                "Connect",
                "Disconnect",
                "Set System Proxy",
                "Reset System Proxy",
                "Show",
                "Exit",
            ],
        ]
        self.tooltip = "Free Surf!"
        if inside_windows():
            self.tray = SystemTray(
                self.menu,
                single_click_events=False,
                window=self.window,
                tooltip=self.tooltip,
                icon="assets/icons/picon_yellow.png",
            )
        # else:
        #     self.tray = SystemTray(
        #         self.menu,
        #         single_click_events=False,
        #         window=self.window,
        #         tooltip=self.tooltip,
        #     )

    def _read_gui_config(self):
        # print(f"{config_path()}/gui/config.json")
        folder_path = f"{config_path()}\\gui\\"
        if not inside_windows():
            folder_path = folder_path.replace("\\", "/")
        path = f"{folder_path}config.json"

        if not FactorySetting.check_file_or_folder_exists(path):
            FactorySetting.make_config_folder_ready(folder_path)
            with open(path, "w") as file:
                file.write(FactorySetting.gui_config)

        with open(
            path,
            "r",
        ) as json_file:
            # Load the JSON data from the file
            self.gui_data = json.load(json_file)

    def _update_debug(self):
        with io.StringIO() as buffer, redirect_stdout(buffer):
            while True:
                time.sleep(self.referesh_terminal_period)
                output = buffer.getvalue()
                if len(output) > 10:
                    buffer.flush()
                if len(output) > len(self.mline_text):
                    self.mline_text = output
                    try:
                        self.window["debug_box"].update(value=self.mline_text)
                    except:
                        pass

    def _getLayout(self) -> list:
        return self.layout

    def load_settings(self):
        path = f"{config_path()}\\gui\\config.json"
        if not inside_windows():
            path = path.replace("\\", "/")
        # print("gui path:", path)
        with open(
            path,
            "r",
        ) as json_file:
            self.settings = json.load(json_file)

        print(self.settings)

        self.num_fragment = int(self.settings["num_of_fragments"])
        self.cloudflare_ip = self.settings["cloudflare_address"]

    def save_gui(self):
        use_fragmentation = bool(self.window["use_fragmentation"].get())

        path = f"{config_path()}\\gui\\config.json"
        if not inside_windows():
            path = path.replace("\\", "/")
        # print("gui path:", path)
        with open(
            path,
            "w",
        ) as json_file:
            # Write the JSON data to the file
            try:
                self.gui_data["local_port"] = self.window["local_port"].get()
                self.gui_data["use_fragmentation"] = use_fragmentation
                self.gui_data["subscription"] = self.window["subscription"].get()
            except:
                print("Cannot save gui.")
                ################################################
            try:
                self.gui_data["selected_profile_name"] = self.selected_profile_name
                self.gui_data["selected_profile_number"] = self.selected_profile_number
            except:
                print("Cannot save gui.")
                ###########################
            try:
                self.gui_data["keep_top"] = self.settings["keep_top"]
                self.gui_data["close_to_tray"] = self.settings["close_to_tray"]
                self.gui_data["auto_connect"] = self.settings["auto_connect"]
                self.gui_data["start_minimized"] = self.settings["start_minimized"]
                self.gui_data["cloudflare_address"] = self.settings[
                    "cloudflare_address"
                ]
                self.gui_data["segmentation_timeout"] = self.settings[
                    "segmentation_timeout"
                ]
                self.gui_data["num_of_fragments"] = self.settings["num_of_fragments"]

            except Exception as e:
                print("Cannot save gui.")

            json.dump(self.gui_data, json_file)

    def generate_menu(self):
        menu_def = [
            [
                "File",
                [
                    "New",
                    ["New Vless", "New Vmess", "New Trojan", "New Gost"],
                    "Settings",
                    "Exit",
                ],
            ],
            [
                "Import Config",
                [
                    # "From QR Code",
                    "From Clipboard",
                    "From Json File",
                ],
            ],
            [
                "Export Config",
                [
                    "To QR Code",
                    "To Clipboard",
                    "To Json File",
                ],
            ],
            [
                "Download Bins",
                [
                    "Download Xray",
                    "Download Gost",
                    "Download SingBox",
                ],
            ],
            [
                "Help",
                [
                    "About",
                    "Upgrade V2RayP",
                    "Force Kill Xray,Gost",
                ],
            ],
        ]
        return psg.Menu(menu_def)

    def generate_top_part(self):
        try:
            default_use_fragmentation = self.gui_data["use_fragmentation"]
        except:
            default_use_fragmentation = False

        conn = [
            psg.Button("(Re)Connect", key="connect"),
            psg.Button("Disconnect", key="disconnect"),
            psg.Checkbox(
                text="Use Fragmentation",
                key="use_fragmentation",
                default=default_use_fragmentation,
            ),
            psg.Text("Local Port:"),
            psg.InputText(
                default_text=self.gui_data["local_port"], key="local_port", size=(5,)
            ),
        ]

        profile = [
            psg.Button(
                "Edit",
                key="edit",
            ),
            psg.Button("Delete", key="delete"),
        ]

        control = [
            psg.Button("HidetoTray", key="hide") if inside_windows() else psg.Text(""),
            psg.Button("Referesh", key="referesh"),
        ]

        ret = [
            psg.Frame("Connection", [conn]),
            psg.Frame("Profile", [profile]),
            psg.Frame("Control", [control]),
        ]
        return ret

    def generate_Table(self):
        toprow, self.rows = self.referesh_table_content()

        tbl1 = psg.Table(
            values=self.rows,
            headings=toprow,
            auto_size_columns=True,
            display_row_numbers=True,
            justification="center",
            key="-TABLE-",
            selected_row_colors="red on yellow",
            enable_events=True,
            expand_x=True,
            expand_y=True,
            enable_click_events=True,
            vertical_scroll_only=False,
            right_click_menu=self.right_click_generator(),
        )
        return tbl1

    def referesh_table_content(self):
        toprow = [
            "Type",
            "Remark",
            "Address",
            "Port",
            "Security",
            "Transport",
            "TLS",
            "Subgroup",
            "Delay",
            "Speed (M/s)",
        ]

        rows = []

        # self.rows_dict = RefereshTableContent().referesh_v2ray_subscription_folder(
        #     subscription_name
        # )

        # for row_dict in self.rows_dict:
        #     row = [
        #         row_dict["protocol"],
        #         row_dict["remark"],
        #         row_dict["server_address"],
        #         row_dict["port"],
        #         row_dict["user_security"],
        #         row_dict["network"],
        #         row_dict["security"],
        #         subscription_name,
        #         "",
        #     ]
        #     rows.append(row)

        self.rows_dict = (RefereshTableContent()).extract_all_rows()
        # rows = []
        for row_dict in self.rows_dict:
            row = [
                row_dict["protocol"],
                row_dict["remark"],
                row_dict["server_address"],
                row_dict["port"],
                row_dict["user_security"],
                row_dict["network"],
                row_dict["security"],
                row_dict["group"],
                "",
            ]
            rows.append(row)
        return toprow, rows

    def generate_ConsoleBox(self):
        Console_box = psg.MLine(
            size=(40, 10),
            font=("", 7),
            default_text="",
            key="debug_box",
            justification="left",
            expand_x=True,
            autoscroll=True,
        )
        return Console_box

    def Hide(self):
        self.window.Hide()
        self.isHide = True

    def UnHide(self):
        self.window.UnHide()
        self.window.normal()
        self.window.BringToFront()

        self.isHide = False

    def toggle_hide(self):
        if self.isHide == False:
            self.Hide()
        else:
            self.UnHide()

    def right_click_generator(self):
        rightclick = [
            "&RightClick",
            [
                "&Connect",
                "&Disconnect",
                #  "&Speed Test",
                "Delay &of Current Connection",
                "&Exit",
            ],
        ]
        return rightclick

    def check_connection(self):
        self.thread_exit = threading.Event()
        while self.enable_loops:
            print("connection checking...")

            self.isConnected = NetTools.is_connected_to_internet(
                "https://www.yahoo.com", int(self.local_port)
            )
            if inside_windows():
                if self.isConnected and inside_windows:
                    self.tray.change_icon("assets/icons/picon_green.png")
                else:
                    self.tray.change_icon("assets/icons/picon_red.png")
                # time.sleep(5)
            self.thread_exit.wait(5)

    def Hide_Show_Notification(self, text="Minimized to tray!"):
        if self.first_minimized is True:
            self.tray.show_message("Best Proxy", text)

        self.Hide()
        self.first_minimized = False

    def ping_test(self):
        try:
            sel = self.connected_selected_number
        except:
            psg.popup("First connect by clicking connect!")
            return

        proxy_address = "127.0.0.1"
        proxy_address_port = int(self.local_port)
        target_host = "https://google.com"
        target_port = 80
        ping_delay = NetTools.measure_ping_through_socks_proxy(
            proxy_address, proxy_address_port, target_host
        )
        if ping_delay:
            print(
                f"Ping delay to {target_host}:{target_port} via the proxy: {ping_delay:.3f} milli-seconds"
            )
            self.rows[sel][8] = ping_delay
            self.window["-TABLE-"].update(values=self.rows, select_rows=[sel])
        else:
            self.rows[sel][8] = -1
            self.window["-TABLE-"].update(values=self.rows, select_rows=[sel])

    def run_GFW(self):
        if self.gfw_interface:
            self.gfw_interface.stop()
        self.gfw_interface = GFW_Interface(
            int(self.settings["num_of_fragments"]),
            self.GFW_port,
            self.settings["cloudflare_address"],
            self.cloudflare_port,
            int(self.settings["segmentation_timeout"]),
        )

    def v2ray_to_url(self, sel):
        filename = str(self.rows_dict[sel]["remark"])
        protocol = str(self.rows_dict[sel]["protocol"])

        ##################
        group = str(self.rows_dict[sel]["group"])
        if len(group) > 1:
            group_path = f"\\subscriptions\\{group}"
        else:
            group_path = ""
        ################
        pname = filename.replace(".json", "")
        path = f"{config_path()}\\v2ray_profiles{group_path}\\{filename}"
        if not inside_windows():
            path = path.replace("\\", "/")
        if protocol in ("vless", "vmess", "trojan"):
            v2ray_text = ExportURLfromConfig(
                path,
                pname,
            ).share_link()

            return v2ray_text

    def delete(self):
        try:
            sel = int(self.window["-TABLE-"].widget.selection()[0]) - 1
        except:
            return
        filename = self.rows_dict[sel]["remark"]
        protocol = self.rows_dict[sel]["protocol"]
        group = self.rows_dict[sel]["group"]

        if len(group) > 1:
            group_path = f"\\subscriptions\\{group}"

        else:
            group_path = ""

        if protocol in ("vless", "vmess", "trojan"):
            cmd = f'del "{config_path()}\\v2ray_profiles{group_path}\\{filename}"'
            print(cmd)
            if not inside_windows():
                cmd = cmd.replace("\\", "/")

            os.popen(cmd).read()
        else:
            os.popen(
                f'del "{config_path()}\\gost_profiles\\{filename}"'
                if inside_windows()
                else f'rm "{config_path()}/gost_profiles/{filename}"'
            ).read()
        _, rows = self.referesh_table_content()
        self.window["-TABLE-"].update(rows)

    def disconnect(self):
        if self.gfw_interface:
            self.gfw_interface.stop()

        self.enable_loops = False
        try:
            self.connectv2ray.kill()
            # self.connectv2ray = None
        except Exception as e:
            print("error in killing", e)

        try:
            print(self.connect_gost)
            self.connect_gost.kill()
            # self.connect_gost = None
        except Exception as e:
            print("error in killing", e)

        try:
            self.thread_exit.set()
            self.thrd_check_connection.join(1)
            # self.thrd_icon = None
            self.tray.change_icon("assets/icons/picon_yellow.png")
        except:
            pass
        self.window["connection_name"].update("disconnected")
        print("Killed, disconnected!")

    def generate_random_filename(self):
        random_uuid = uuid.uuid4()
        filename = str(random_uuid)
        return filename[0:5]

    def import_config_file(self):
        file_path = FileBrowser().get_file_path()

        if not file_path:
            return
        with open(file_path, "r") as json_file:
            # Write the JSON data to the file
            data = json.load(json_file)
        try:
            protocol = data["outbounds"][0]["protocol"]
        except:
            protocol = data["remote_protocol"]

        if protocol in ("vless", "vmess", "trojan"):
            try:
                address = data["outbounds"][0]["settings"]["servers"][0]["address"]
            except:
                address = data["outbounds"][0]["settings"]["vnext"][0]["address"]

            file_name = f"{protocol}-{address}-{self.generate_random_filename()}.json"

            with open(
                f"{config_path()}\\v2ray_profiles\\{file_name}"
                if inside_windows()
                else f"{config_path()}/v2ray_profiles/{file_name}",
                "w",
            ) as json_file:
                json.dump(data, json_file)
        else:
            address = data["remote_address"]
            file_name = f"{protocol}-{address}-{self.generate_random_filename()}.json"

            with open(
                f"{config_path()}\\gost_profiles\\{file_name}"
                if inside_windows()
                else f"{config_path()}/gost_profiles/{file_name}",
                "w",
            ) as json_file:
                json.dump(data, json_file)

        _, rows = self.referesh_table_content()
        self.window["-TABLE-"].update(rows)

    def export_config_file(self):
        destination_folder_path = FileBrowser().get_folder_path()
        print("dest:", destination_folder_path)
        if not destination_folder_path:
            return
        sel = int(self.window["-TABLE-"].widget.selection()[0]) - 1
        filename = self.rows_dict[sel]["remark"]
        protocol = self.rows_dict[sel]["protocol"]
        if protocol in ("vless", "vmess", "trojan"):
            config_folder_path = "configs/v2ray_profiles"
        else:
            config_folder_path = "configs/gost_profiles"
        cmd = (
            f"copy {config_folder_path}/{filename} {destination_folder_path}/{filename}"
        )
        cmd = cmd.replace("/", "\\")
        os.popen(cmd)

    def paste_v2ray(self, url=None):
        if url == None:
            url = pyperclip.paste()
        if ("trojan" in url) or ("vless" in url) or ("vmess" in url):
            config_json = json.loads(generateConfig(url))
            profileName = config_json["_comment"]["remark"]
            config_json["inbounds"][0]["port"] = int(self.local_port)
            # config_json["inbounds"][1]["port"] = int(self.local_port) + 1
            path = f"{config_path()}\\v2ray_profiles\\"

            if not inside_windows():
                path = path.replace("\\", "/")
            try:
                os.mkdir(path)
            except:
                pass
            with open(
                f"{path}{profileName}.json",
                "w",
            ) as f:
                json.dump(config_json, f)

        else:
            path = f"{config_path()}\\gost_profiles\\"
            config_json = url
            profileName = f'{url["remote_protocol"]}_{url["remote_port"]}'
            if not inside_windows():
                path = path.replace("\\", "/")
            try:
                os.mkdir(path)
            except:
                pass
            with open(
                f"{path}{profileName}.json",
                "w",
            ) as f:
                json.dump(config_json, f)

        _, rows = self.referesh_table_content()
        self.window["-TABLE-"].update(rows)
        # if ("trojan" in url) or ("vless" in url) or ("vmess" in url):
        #     ut = URLTools_for_V2Ray(url, int(self.local_port))
        #     config = ut.toJsonConfigString()
        #     with open(f"{os.getenv('USERPROFILE')}\\appdata\\roaming\v2rayp\configs\\v2ray_profiles\\{ut.profileName}.json", "w") as f:
        #         f.write(config)
        # _, rows = self.referesh_table_content()
        # self.window["-TABLE-"].update(rows)

    def connect(self, sel):
        self.disconnect()

        self.enable_loops = True
        filename: str = self.rows_dict[sel]["remark"]
        protocol = self.rows_dict[sel]["protocol"]
        #########################################
        if protocol in ("vless", "vmess", "trojan"):
            path = f"{config_path()}/bin/xray"
            if inside_windows():
                path = f"{path}.exe"
            if not os.path.isfile(path):
                resp = psg.popup_ok_cancel("Please download Xray", keep_on_top=True)
                print(resp)
                if resp == "OK":
                    self.download_module("xray")
                    # threading.Thread(target=self.download_xray, daemon=True).start()
                    return
        else:
            path = f"{config_path()}/bin/gost"
            if inside_windows():
                path = f"{path}.exe"
            if not os.path.isfile(path):
                resp = psg.popup_ok_cancel("Please download gost", keep_on_top=True)
                if resp == "OK":
                    self.download_module("gost")
                    return
        #######################################
        use_fragmentation = bool(self.window["use_fragmentation"].get())
        group = self.rows_dict[sel]["group"]
        #####################
        if use_fragmentation:
            ch = psg.popup_ok_cancel(
                "The fragmentation is selected!\nAre you sure?",
                title="Warning",
                keep_on_top=True,
            )
            if ch == "Cancel":
                return

        if protocol in ("vless", "vmess", "trojan"):  # using v2ray
            #####################
            if len(group) >= 1:
                group_path = f"\\subscriptions\\{group}"
            else:
                group_path = ""
            #########################
            config_file_path = (
                f"{config_path()}\\v2ray_profiles{group_path}\\{filename}"
            )
            if not inside_windows():
                config_file_path = config_file_path.replace("\\", "/")
            if use_fragmentation:
                self.make_fragmentation_config_v2ray(config_file_path)
                self.run_GFW()
                config_file_path = (
                    f"{config_path()}\\v2ray_profiles\\fragment\\temp.json"
                )
                if not inside_windows():
                    config_file_path = config_file_path.replace("\\", "/")

            self.connectv2ray = ConnectV2Ray(config_file_path, self.local_port)
            self.connectv2ray.connect()
        else:  # using gost
            config_file_path = f"{config_path()}\\gost_profiles\\{filename}"
            if not inside_windows():
                config_file_path = config_file_path.replace("\\", "/")
            if use_fragmentation:
                self.make_fragmentation_config_gost(config_file_path)
                self.run_GFW()
                config_file_path = (
                    f"{config_path()}\\gost_profiles\\fragment\\temp.json"
                )
                if not inside_windows():
                    config_file_path = config_file_path.replace("\\", "/")

            self.connect_gost = ConnectGost(config_file_path, self.local_port)
            self.connect_gost.connect()

        self.window["connection_name"].update(filename.replace(".json", ""))

        self.thrd_check_connection = threading.Thread(target=self.check_connection)
        self.thrd_check_connection.start()
        ##############

    def make_fragmentation_config_v2ray(self, file_path):
        with open(f"{file_path}", "r") as json_file:
            # Load the JSON data from the file
            json_data = json.load(json_file)
        self.protocol = json_data["outbounds"][0]["protocol"]

        if self.protocol in ("vless", "vmess"):
            address = json_data["outbounds"][0]["settings"]["vnext"][0]["address"]
            port = json_data["outbounds"][0]["settings"]["vnext"][0]["port"]
            json_data["outbounds"][0]["settings"]["vnext"][0]["address"] = "127.0.0.1"
            json_data["outbounds"][0]["settings"]["vnext"][0]["port"] = self.GFW_port
        elif self.protocol == "trojan":
            address = json_data["outbounds"][0]["settings"]["servers"][0]["address"]
            port = json_data["outbounds"][0]["settings"]["servers"][0]["port"]
            json_data["outbounds"][0]["settings"]["servers"][0]["address"] = "127.0.0.1"
            json_data["outbounds"][0]["settings"]["servers"][0]["port"] = self.GFW_port

        self.cloudflare_port = port
        print("This is port", self.cloudflare_port)
        cmd = f"mkdir {config_path()}\\v2ray_profiles\\fragment"
        if not inside_windows():
            cmd = cmd.replace("\\", "/")
        os.popen(cmd).read()
        config_file_path = f"{config_path()}\\v2ray_profiles\\fragment\\temp.json"
        if not inside_windows():
            config_file_path = config_file_path.replace("\\", "/")
        with open(
            config_file_path,
            "w",
        ) as json_file:
            # Write the JSON data to the file
            json.dump(json_data, json_file)

    def make_fragmentation_config_gost(self, file_path):
        with open(f"{file_path}", "r") as json_file:
            # Load the JSON data from the file
            json_data = json.load(json_file)
        self.cloudflare_port = int(json_data["remote_port"])
        json_data["sni"] = json_data["remote_address"]
        json_data["remote_address"] = "127.0.0.1"
        json_data["remote_port"] = self.GFW_port
        cmd = f"mkdir {config_path()}\\gost_profiles\\fragment"
        if not inside_windows():
            cmd = cmd.replace("\\", "/")
        os.popen(cmd).read()
        path = f"{config_path()}\\gost_profiles\\fragment\\temp.json"
        if not inside_windows():
            path = path.replace("\\", "/")
        with open(
            path,
            "w",
        ) as json_file:
            # Write the JSON data to the file
            json.dump(json_data, json_file)

    def edit_profile_page(self, sel):
        filename = self.rows_dict[sel]["remark"]
        protocol = self.rows_dict[sel]["protocol"]
        group = self.rows_dict[sel]["group"]

        if protocol in ("vless", "vmess", "trojan"):
            page_data: dict = RefereshEditPage(filename, group).get_editpage_content()
            new_data = None
            if protocol == "trojan":
                new_data = TrojanGUI(page_data).start_window()
            elif protocol == "vless":
                new_data = VlessGUI(page_data).start_window()
            elif protocol == "vmess":
                new_data = VmessGUI(page_data).start_window()

            if new_data:
                page_data.update(new_data)
                SaveGUIConfigPage(filename, page_data, False, group)

        else:
            new_data = GostGUI(filename).start_window()
            SaveGUIConfigPage(filename, new_data)

    def set_reset_system_proxy(self, mode="reset"):
        if mode == "set":
            cmd = f'reg add \\"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\\" /v ProxyEnable /t REG_DWORD /d 1 /f && reg add \\"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\\" /v ProxyServer /t REG_SZ /d \\"socks=127.0.0.1:7595\\" /f'

        elif mode == "reset":
            cmd = 'reg add \\"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\\" /v ProxyEnable /t REG_DWORD /d 0 /f'

        cmd2 = f"powershell Start-Process -WindowStyle Hidden cmd.exe -argumentlist '/k \"{cmd}\"' -Verb Runas; exit"
        subprocess.Popen(cmd2, shell=True)

    def run_command_as_admin(self, cmd):
        cmd2 = f"powershell Start-Process -WindowStyle Hidden cmd.exe -argumentlist '/k \"{cmd}\"' -Verb Runas"
        os.popen(cmd2).read()

    def set_settings_gui(self):
        settings = SettingGUI(self.gui_data).start_window()

        if settings:
            if settings == "factory_reset":
                self.restart()
                return

            self.settings.update(settings)
            self.root_of_windows.attributes("-topmost", self.settings["keep_top"])
            if self.settings["close_to_tray"]:
                self.root_of_windows.protocol(
                    "WM_DELETE_WINDOW", self.Hide_Show_Notification
                )
            else:
                self.root_of_windows.protocol("WM_DELETE_WINDOW", self.Exit)

    def Exit(self):
        try:
            self.tray.close()
        except:
            pass
        self.save_gui()
        self.enable_loops = False
        self.disconnect()
        self.window.close()
        exit()

    def about_generator(self):
        string_about = f"The version of V2RayP is {__version__}.\n\n"

        gost_about_path = f"{config_path()}\\bin\\gost.exe"
        if not inside_windows():
            gost_about_path = gost_about_path.replace("\\", "/").replace(".exe", "")
        print(gost_about_path)
        xray_about_path = f"{config_path()}\\bin\\xray.exe"
        if not inside_windows():
            xray_about_path = xray_about_path.replace("\\", "/").replace(".exe", "")
        gost_string = []
        if os.path.isfile(gost_about_path):
            gost_string = os.popen(gost_about_path + " -V").read().strip()
        xray_string = []
        if os.path.isfile(xray_about_path):
            xray_string = os.popen(xray_about_path + " version").read().strip()

        layout = [
            [psg.Text("The V2RayP Version:\t\t"), psg.Text(__version__)],
            [psg.Text("The Xray Version:\t\t"), psg.Text(xray_string)]
            if xray_string
            else [],
            [psg.Text("The Gost Version:\t\t"), psg.Text(gost_string)]
            if gost_string
            else [],
            [psg.Button("OK")],
        ]
        window = psg.Window(
            title="About", layout=layout, keep_on_top=True, size=(600, 200)
        )

        window.read()
        window.close()

        # psg.popup_ok(string_about, title="About")

    def init_window(self):
        layout = self._getLayout()
        self.cloudflare_ip = self.settings["cloudflare_address"]
        keep_on_top = self.settings["keep_top"]
        self.window = psg.Window(
            "V2rayP",
            icon="assets/icons/appicon.ico",
            layout=layout,
            size=(width, 600),
            resizable=True,
            # no_titlebar=True,
            finalize=True,
            grab_anywhere=True,
            keep_on_top=keep_on_top,
        )
        self.root_of_windows = self.window.TKroot

        def copy(temp):
            sel = self.selected_profile_number
            pyperclip.copy(self.v2ray_to_url(sel))

        def paste(temp):
            self.paste_v2ray()

        self.root_of_windows.bind("<Control-c>", copy)
        self.root_of_windows.bind("<Control-v>", paste)

        if self.settings["close_to_tray"]:
            self.root_of_windows.protocol(
                "WM_DELETE_WINDOW", self.Hide_Show_Notification
            )
        else:
            self.root_of_windows.protocol("WM_DELETE_WINDOW", self.Exit)
        try:
            self.window["-TABLE-"].update(
                select_rows=[self.gui_data["selected_profile_number"]]
            )
        except:
            pass

    def download_module(self, bin_name):
        self.disconnect()
        print("*************************")
        print("Disconnected to download.")
        self.progressbar_window = None
        layout = [
            [psg.ProgressBar(100, key="progressbar2", size=(35, 20))],
            [psg.Text(key="percentage")],
            [psg.Button("Cancel")],
        ]
        self.progressbar_window = psg.Window(
            f"Downloading {bin_name}...", layout=layout, keep_on_top=True, finalize=True
        )
        enable_download = pass_by_ref()
        enable_download.value = True

        threading.Thread(
            target=download_xray_gost,
            args=(self.progressbar_window, enable_download, bin_name),
        ).start()
        while True:
            event, values = self.progressbar_window.read(timeout=2000)
            if (
                event in (None, "Cancel", psg.WIN_CLOSED)
                or "100" in self.progressbar_window["percentage"].get()
            ):
                enable_download.value = False
                print(enable_download.value)
                self.progressbar_window.close()

                break
        self.progressbar_window.close()

    def upgrade_v2rayp(self):
        resp = psg.popup_ok_cancel(
            "Do you want to update from here?\nAfter upgrading you should exit and open v2rayp again.",
            title="Upgrading...",
        )
        print(resp)
        if resp == "OK":
            cmd = f"{sys.executable} -m pip install --upgrade v2rayp"
            print(cmd)

            window = psg.Window(
                "Upgradig...",
                [[psg.MLine(key="debug2", size=(40, 40))]],
                finalize=True,
                keep_on_top=True,
            )
            window["debug2"].update("Upgrading...")

            p = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            run = True

            def get_process_status():
                nonlocal run
                while True:
                    time.sleep(1)
                    run = p.poll() is None

                    if run == False:
                        break

            threading.Thread(target=get_process_status).start()

            def update_inside():
                nonlocal run
                lines = ""
                while run:
                    line = p.stdout.readline().decode().strip()
                    lines += line
                    window["debug2"].update(lines)
                    time.sleep(0.1)
                window.close()

            threading.Thread(target=update_inside).start()

    def start_window(self):
        self.load_settings()
        self.init_window()
        self.UnHide()
        self._generate_tray()

        self.firstTime = True
        while True:
            event, values = self.window.read()

            try:
                sel = int(self.window["-TABLE-"].widget.selection()[0]) - 1
                self.selected_profile_number = sel
                self.selected_profile_name = self.rows_dict[sel]["remark"]
            except:
                pass
            self.local_port = self.window["local_port"].get()

            if self.firstTime:
                self.window["-TABLE-"].bind("<Return>", "_Enter")
                self.window["-TABLE-"].bind(
                    "<Double-Button-1>", "-double-"
                )  # double click event in table
                self.firstTime = False
            #################
            if inside_windows():
                if event == self.tray.key:
                    event = values[event]
            ##################
            if event in ("exit", "Exit"):
                break
            elif event == "save":
                self.save_gui()
            #############################################
            elif (event in ("connect", "Connect")) or ("Enter" in event):
                self.connected_selected_number = self.selected_profile_number
                try:
                    self.connect(sel)

                except Exception as e:
                    print("Error717 in connection:", str(e))

            elif event in ("disconnect", "Disconnect"):
                threading.Thread(target=self.disconnect).start()

            ################################
            elif event == "referesh":
                _, rows = self.referesh_table_content()
                self.window["-TABLE-"].update(
                    rows, select_rows=[self.selected_profile_number]
                )
            #############################################
            elif ("edit" in event) or ("-double-" in event):
                try:
                    print(sel)
                except:
                    continue
                self.edit_profile_page(sel)

            ######################
            elif "From Clipboard" in event:
                self.paste_v2ray()
            elif event == "delete":
                self.delete()
            elif "To Clipboard" in event:
                pyperclip.copy(self.v2ray_to_url(sel))
            #######################
            elif event in ("hide", "Hide"):
                self.Hide_Show_Notification()

            elif event == "__DOUBLE_CLICKED__":
                # self.toggle_hide()
                self.UnHide()

            elif event == "Show":
                self.UnHide()
            #######################right-click
            elif "Delay" in event:
                threading.Thread(target=self.ping_test).start()
                # self.ping_test()
            #####################
            elif event == "From Json File":
                try:
                    self.import_config_file()
                except:
                    pass
            elif event == "To Json File":
                self.export_config_file()
            ##############################
            elif event == "Set System Proxy":
                self.set_reset_system_proxy("set")
            elif event == "Reset System Proxy":
                self.set_reset_system_proxy("reset")
            ##############################
            elif event == "Settings":
                self.set_settings_gui()

            ###################################
            elif event == "To QR Code":
                QRCode(self.v2ray_to_url(sel))
            #################################
            elif event == "update_subscription":
                if Subscriptions(values["subscription"]).make_subscription():
                    _, rows = self.referesh_table_content()
                    self.window["-TABLE-"].update(
                        rows, select_rows=[self.selected_profile_number]
                    )

            elif event == "delete_subscription":
                Subscriptions().delete_previous_folder()
                _, rows = self.referesh_table_content()
                try:
                    self.window["-TABLE-"].update(
                        rows, select_rows=[self.selected_profile_number]
                    )
                except:
                    self.window["-TABLE-"].update(rows)

            ##############################3
            elif event == "Force Kill Xray,Gost":
                if inside_windows():
                    os.popen("taskkill /f /im xray.exe").read()
                    os.popen("taskkill /f /im gost.exe").read()
                else:
                    os.popen("killall -9 xray").read()
                    os.popen("killall -9 gost").read()
                self.disconnect()
                print("Forced to be killed!")

            elif event == "Upgrade V2RayP":
                self.upgrade_v2rayp()
            elif event == "About":
                self.about_generator()

            ###############################
            elif event == "Download Xray":
                resp = psg.popup_yes_no(
                    "Are you sure you want to download?", keep_on_top=True
                )
                if resp == "No":
                    continue
                self.download_module("xray")
            elif event == "Download Gost":
                resp = psg.popup_yes_no(
                    "Are you sure you want to download?", keep_on_top=True
                )
                if resp == "No":
                    continue
                self.download_module("gost")
            ###################################
            elif event == "shortcut":
                if inside_windows():
                    path = (
                        os.popen(r"echo %userprofile%\\desktop\\v2rayp.cmd")
                        .read()
                        .strip()
                    )

                    exec = sys.executable.replace("python.exe", "pythonw.exe").replace(
                        "python3.exe", "pythonw.exe"
                    )
                    with open(path, "w") as file:
                        file.write(f"start /min {exec} -m v2rayp")
                else:
                    userhome = os.path.expanduser("~")
                    path = userhome + "/Desktop"

                    path = f"{path}/v2rayp.sh"
                    print(path)
                    with open(path, "w") as file:
                        file.write(f"{sys.executable} -m v2rayp")
                    os.popen(f"chmod +x {path}")

            ###############################
            else:
                self.check_new_file_event(event)
            ################################

        self.Exit()

    def check_new_file_event(self, event):
        if "New Vless" in event:
            page_data = VlessGUI().start_window()
            if page_data:
                page_data["protocol"] = "vless"
                url = ExportURLfromConfig.construc_simple_link_from_edit_page(page_data)
                self.paste_v2ray(url)

        elif "New Vmess" in event:
            page_data = VmessGUI().start_window()
            if page_data:
                page_data["protocol"] = "vmess"
                url = ExportURLfromConfig.construc_simple_link_from_edit_page(page_data)
                self.paste_v2ray(url)

        elif "New Trojan" in event:
            page_data = TrojanGUI().start_window()
            if page_data:
                page_data["protocol"] = "trojan"
                url = ExportURLfromConfig.construc_simple_link_from_edit_page(page_data)
                self.paste_v2ray(url)

        elif "New Gost" in event:
            page_data = GostGUI(None).start_window()
            if page_data:
                self.paste_v2ray(page_data)

    def restart(self):
        python = sys.executable
        os.execv(python, [python] + sys.argv)
        # exit()


if __name__ == "__main__":
    # print("filename is: ", __file__)
    # procs = [
    #     [p]
    #     for p in psutil.process_iter()
    #     if "python" in p.name() and __file__ in p.cmdline()
    # ]
    def is_another_instance_running():
        current_process = psutil.Process()
        if inside_windows():
            filename = __file__.split("\\")[-1]
        else:
            filename = __file__.split("/")[-1]

        print(filename)
        cnt = 0
        for process in psutil.process_iter(["pid", "name"]):
            j = " ".join(current_process.cmdline())

            if (
                "python" in process.info["name"]
                and (filename in j)
                and ("debug" not in j)
            ):
                print(current_process.cmdline())
                cnt += 1
            if "Code" in process.info["name"]:
                print(j)
                return False
        if cnt > 2:  # 2 because it runs init and then v2rayp
            return True
        return False

    # if is_another_instance_running():
    #     print("Another instance is running.")
    # else:
    #     print("No other instances are running.")

    if is_another_instance_running():
        print("Process is already running...")
        resp = psg.popup_yes_no(
            "Another process is running.\nAre you sure you want to continue?",
            keep_on_top=True,
        )
        if resp == "No":
            exit()
    MainGUI().start_window()
