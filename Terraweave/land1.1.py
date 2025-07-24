import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import random
import os
from collections import deque

# ==============================================================================
# 核心美術與邏輯定義 (微調參數)
# ==============================================================================
TILE_PATTERNS = {
    1: [[1,1,1,1,1,1,1], [1,0,0,0,0,0,1], [1,0,0,0,0,0,1], [1,0,0,0,0,0,1], [1,0,0,0,0,0,1], [1,0,0,0,0,0,1], [1,1,1,1,1,1,1]],
    2: [[0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [1,1,1,1,1,1,1], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0]],
    3: [[1,1,0,0,0,0,0], [1,1,1,0,0,0,0], [0,1,1,1,0,0,0], [0,0,1,1,1,0,0], [0,0,0,1,1,1,0], [0,0,0,0,1,1,1], [0,0,0,0,0,1,1]],
    4: [[0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0]],
    5: [[1,1,0,0,0,1,1], [1,1,1,0,1,1,1], [0,1,1,1,1,1,0], [0,0,1,1,1,0,0], [0,1,1,1,1,1,0], [1,1,1,0,1,1,1], [1,1,0,0,0,1,1]],
    6: [[0,0,0,0,0,0,0], [1,1,1,1,1,1,1], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [0,0,0,0,0,0,0], [1,1,1,1,1,1,1], [0,0,0,0,0,0,0]],
}

class RiverGameGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("河流農場")
        self.master.resizable(False, False)

        self.board_data = [[None for _ in range(6)] for _ in range(4)]
        self.players = ["玩家1", "玩家2"]
        
        self.player_border_colors = {1: "#ffc0cb", 2: "#90ee90"}
        self.player_path_colors = {1: "#d90429", 2: "#006400"}
        self.water_color = "#00BFFF"
        
        self.current_player_index = 0
        self.game_phase = "SETUP"
        self.current_drawn_tile = None
        self.current_rotation = 0
        
        self.base_images = {}
        self.photo_images_cache = {}
        self.dice_images = {}

        try:
            self.main_frame = tk.Frame(self.master, bg="lightgrey", padx=5, pady=5)
            self.main_frame.pack(expand=True, fill="both")
            self.load_images()
            self.create_widgets()
            self.start_initial_setup()
        except Exception as e:
            messagebox.showerror("啟動錯誤", f"無法啟動遊戲: {e}")
            self.master.destroy()

    def load_images(self):
        self.tile_pixel_size = 80
        for i in range(1, 7):
            filepath = os.path.join(os.path.dirname(__file__), f"{i}.png")
            if not os.path.exists(filepath): raise FileNotFoundError(f"板塊圖片遺失: {i}.png")
            img = Image.open(filepath).resize((self.tile_pixel_size, self.tile_pixel_size), Image.LANCZOS)
            self.base_images[i] = img
        
        dice_image_size = (40, 40)
        num_to_word = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six'}
        for i in range(1, 7):
            filename = f"dice-six-faces-{num_to_word[i]}.png"
            filepath = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.exists(filepath): raise FileNotFoundError(f"骰子圖片遺失: {filename}")
            img = Image.open(filepath).resize(dice_image_size, Image.LANCZOS)
            self.dice_images[i] = ImageTk.PhotoImage(img)
        blank_dice_img = Image.new('RGBA', dice_image_size, (0,0,0,0))
        self.dice_blank_image = ImageTk.PhotoImage(blank_dice_img)

    def get_rotated_image(self, tile_type, rotation_state):
        angle = -90 * rotation_state
        cache_key = (tile_type, rotation_state)
        if cache_key not in self.photo_images_cache:
            base_img = self.base_images[tile_type]
            rotated_img = base_img.rotate(angle)
            self.photo_images_cache[cache_key] = ImageTk.PhotoImage(rotated_img)
        return self.photo_images_cache[cache_key]

    def create_widgets(self):
        status_frame = tk.Frame(self.main_frame, padx=10, pady=10)
        status_frame.pack(fill="x")
        self.status_label = tk.Label(status_frame, text="準備開始...", font=("Arial", 14), width=35, anchor="w")
        self.status_label.pack(side="left", expand=True, fill="x")
        self.current_tile_button = tk.Button(status_frame, relief="sunken", state="disabled", command=self.rotate_current_tile)
        self.current_tile_button.pack(side="left", padx=10)
        self.dice_text_label = tk.Label(status_frame, text="骰子:", font=("Arial", 14))
        self.dice_text_label.pack(side="left")
        self.dice_image_label = tk.Label(status_frame)
        self.dice_image_label.pack(side="left", padx=(5,0))

        board_width = 6 * self.tile_pixel_size
        board_height = 4 * self.tile_pixel_size
        self.board_canvas = tk.Canvas(self.main_frame, width=board_width, height=board_height, bg="white")
        self.board_canvas.pack(pady=10)
        self.board_canvas.bind("<Button-1>", self.on_canvas_click)
        self.draw_grid_lines()

    def draw_grid_lines(self):
        board_width = 6 * self.tile_pixel_size
        board_height = 4 * self.tile_pixel_size
        for i in range(1, 6): self.board_canvas.create_line(i * self.tile_pixel_size, 0, i * self.tile_pixel_size, board_height, fill="lightgrey")
        for i in range(1, 4): self.board_canvas.create_line(0, i * self.tile_pixel_size, board_width, i * self.tile_pixel_size, fill="lightgrey")

    def on_canvas_click(self, event):
        col = event.x // self.tile_pixel_size
        row = event.y // self.tile_pixel_size
        if 0 <= col < 6 and 0 <= row < 4:
            self.on_board_click(row, col)

    def update_border_color(self):
        player_id = self.current_player_index + 1
        color = self.player_border_colors.get(player_id, "lightgrey")
        self.main_frame.config(bg=color)

    def start_initial_setup(self):
        self.game_phase = "SETUP"
        self.current_player_index = 0
        self.update_border_color()
        self.update_status_label()

    def on_board_click(self, r, c):
        if self.board_data[r][c] is not None: return
        if self.game_phase == "SETUP":
            player_id = self.current_player_index + 1
            self.place_tile_on_board(r, c, 4, player_id, 0)
            if self.current_player_index == 0:
                self.current_player_index = 1
                self.update_border_color()
                self.update_status_label()
            else:
                self.game_phase = "PLAYING"
                self.current_player_index = 0
                self.start_player_turn()
        elif self.game_phase == "PLAYING":
            if self.current_drawn_tile is None: return
            player_id = self.current_player_index + 1
            tile_type = self.current_drawn_tile
            owner = player_id if tile_type == 4 else None
            self.place_tile_on_board(r, c, tile_type, owner, self.current_rotation)
            self.current_drawn_tile = None
            self.current_rotation = 0
            self.dice_image_label.config(image=self.dice_blank_image)
            self.current_tile_button.config(state="disabled")
            if self.is_board_full(): self.end_game(); return
            self.current_player_index = 1 - self.current_player_index
            self.start_player_turn()
            
    def place_tile_on_board(self, r, c, tile_type, owner_id, rotation):
        self.board_data[r][c] = (tile_type, owner_id, rotation)
        photo_image = self.get_rotated_image(tile_type, rotation)
        x = c * self.tile_pixel_size + self.tile_pixel_size / 2
        y = r * self.tile_pixel_size + self.tile_pixel_size / 2
        self.board_canvas.create_image(x, y, image=photo_image, anchor="center")
        if owner_id:
             x1, y1 = c * self.tile_pixel_size, r * self.tile_pixel_size
             self.board_canvas.create_rectangle(x1+2, y1+2, x1+self.tile_pixel_size-2, y1+self.tile_pixel_size-2, outline=self.player_border_colors[owner_id], width=3)
        self.update_water_networks_display()

    def start_player_turn(self):
        self.update_border_color()
        rolled_number = random.randint(1, 6)
        self.current_drawn_tile = rolled_number
        self.current_rotation = 0
        self.dice_image_label.config(image=self.dice_images[rolled_number])
        rotated_image = self.get_rotated_image(self.current_drawn_tile, self.current_rotation)
        self.current_tile_button.config(image=rotated_image, state="normal")
        if self.current_drawn_tile in [1, 4, 5]: self.current_tile_button.config(state="disabled")
        self.update_status_label()
    
    def rotate_current_tile(self):
        if self.current_drawn_tile in [1, 4, 5]: return
        self.current_rotation = (self.current_rotation + 1) % 4
        rotated_image = self.get_rotated_image(self.current_drawn_tile, self.current_rotation)
        self.current_tile_button.config(image=rotated_image)

    def update_status_label(self):
        player = self.players[self.current_player_index]
        if self.game_phase == "SETUP": self.status_label['text'] = f"輪到 {player}：請在地圖上放置你的田地(4)。"
        elif self.game_phase == "PLAYING": self.status_label['text'] = f"輪到 {player}：請放置板塊 {self.current_drawn_tile}。"

    def update_water_networks_display(self):
        self.board_canvas.delete("water_overlay")
        master_grid, _, _, _, source_tiles, all_networks = self.build_and_analyze_grid()
        live_networks = set()
        for i, network in enumerate(all_networks):
            for r_source, c_source in source_tiles:
                if (r_source * 7, c_source * 7) in network:
                    live_networks.add(i); break
        cell_size = self.tile_pixel_size // 7
        for i in live_networks:
            for r, c in all_networks[i]:
                x1, y1 = c * cell_size, r * cell_size
                #self.board_canvas.create_rectangle(x1, y1, x1+cell_size, y1+cell_size, fill=self.water_color, stipple="gray50", outline="", tags="water_overlay")

    def is_board_full(self): return all(all(cell is not None for cell in row) for row in self.board_data)
    
    def end_game(self):
        self.status_label['text'] = "遊戲結束！正在計算分數..."
        self.main_frame.config(bg="lightgrey")
        self.master.update_idletasks()
        master_grid, scores, paths, fields, source_tiles, _ = self.build_and_analyze_grid()
        self.display_results_window(master_grid, paths, fields, source_tiles)
        result_text = f"遊戲結束！\n\n最終得分：\n玩家1: {scores[0]} 分\n玩家2: {scores[1]} 分\n\n"
        if scores[0] > scores[1]: result_text += "玩家1 獲勝！"
        elif scores[1] > scores[0]: result_text += "玩家2 獲勝！"
        else: result_text += "平手！"
        messagebox.showinfo("遊戲結束", result_text)
        self.current_tile_button.config(state="disabled")

    def rotate_matrix(self, matrix):
        return [list(row)[::-1] for row in zip(*matrix)]

    def display_results_window(self, master_grid, paths_by_player, fields_by_player, source_tiles):
        result_window = tk.Toplevel(self.master)
        result_window.title("最終結果路線圖")
        notebook = ttk.Notebook(result_window)
        notebook.pack(pady=10, padx=10, expand=True, fill="both")
        for player_id in [1, 2]:
            player_frame = ttk.Frame(notebook, padding="10")
            notebook.add(player_frame, text=f"玩家 {player_id} 的得分路徑")
            list_frame = tk.Frame(player_frame); list_frame.pack(side="left", fill="y", padx=(0, 10))
            tk.Label(list_frame, text="選擇要檢視的路徑:").pack()
            path_listbox = tk.Listbox(list_frame, selectmode="browse", height=20, width=35); path_listbox.pack(fill="y")
            canvas_frame = tk.Frame(player_frame); canvas_frame.pack(side="right", expand=True, fill="both")
            cell_size = 10
            rows, cols = len(master_grid), len(master_grid[0])
            canvas = tk.Canvas(canvas_frame, width=cols*cell_size, height=rows*cell_size, bg="white"); canvas.pack()
            for r in range(rows):
                for c in range(cols):
                    if master_grid[r][c] == 1:
                        x1, y1, x2, y2 = c*cell_size, r*cell_size, (c+1)*cell_size, (r+1)*cell_size
                        canvas.create_rectangle(x1, y1, x2, y2, fill="lightgrey", outline="")
            for pid, fields in fields_by_player.items():
                for r_field, c_field in fields:
                    x1, y1, x2, y2 = c_field*7*cell_size, r_field*7*cell_size, (c_field+1)*7*cell_size, (r_field+1)*7*cell_size
                    canvas.create_rectangle(x1, y1, x2, y2, outline=self.player_border_colors[pid], width=3)
            for r_source, c_source in source_tiles:
                center_x, center_y = (c_source*7 + 3.5)*cell_size, (r_source*7 + 3.5)*cell_size
                radius = 2.5 * cell_size
                canvas.create_oval(center_x-radius, center_y-radius, center_x+radius, center_y+radius, fill="#4682b4", outline="")
            player_paths = paths_by_player.get(player_id, [])
            for i, path_data in enumerate(player_paths):
                path_listbox.insert(tk.END, f"路線 {i+1}: 田地{path_data['field']} -> 水源{path_data['source']}")
            def on_path_select(event, pl_id=player_id, pl_paths=player_paths, cv=canvas):
                cv.delete("current_path")
                selection_indices = event.widget.curselection()
                if not selection_indices: return
                selected_path_data = pl_paths[selection_indices[0]]
                path, path_color = selected_path_data['path'], self.player_path_colors[pl_id]
                r_field, c_field = selected_path_data['field']
                field_center_x, field_center_y = (c_field*7 + 3.5)*cell_size, (r_field*7 + 3.5)*cell_size
                if path:
                    pixel_path = [(c*cell_size + cell_size/2, r*cell_size + cell_size/2) for r, c in path]
                    start_of_path_x, start_of_path_y = pixel_path[0]
                    cv.create_line(field_center_x, field_center_y, start_of_path_x, start_of_path_y, fill=path_color, width=3, tags="current_path")
                    if len(path) > 1: cv.create_line(pixel_path, fill=path_color, width=3, tags="current_path")
            path_listbox.bind("<<ListboxSelect>>", on_path_select)
            
    def find_all_water_networks(self, master_grid, rows, cols):
        visited, networks = set(), []
        for r in range(rows):
            for c in range(cols):
                if master_grid[r][c] == 1 and (r, c) not in visited:
                    current_network, q = set(), deque([(r, c)])
                    visited.add((r, c))
                    while q:
                        curr_r, curr_c = q.popleft()
                        current_network.add((curr_r, curr_c))
                        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            next_r, next_c = curr_r + dr, curr_c + dc
                            if 0 <= next_r < rows and 0 <= next_c < cols and \
                               master_grid[next_r][next_c] == 1 and (next_r, next_c) not in visited:
                                visited.add((next_r, next_c)); q.append((next_r, next_c))
                    networks.append(current_network)
        return networks

    def build_and_analyze_grid(self):
        master_grid_rows, master_grid_cols = 4 * 7, 6 * 7
        master_grid = [[0] * master_grid_cols for _ in range(master_grid_rows)]
        for r_tile in range(4):
            for c_tile in range(6):
                tile_data = self.board_data[r_tile][c_tile]
                if tile_data:
                    tile_type, _, rotation = tile_data
                    pattern = TILE_PATTERNS.get(tile_type, [[0]*7]*7)
                    for _ in range(rotation): pattern = self.rotate_matrix(pattern)
                    for r_sub in range(7):
                        for c_sub in range(7): master_grid[r_tile*7+r_sub][c_tile*7+c_sub] = pattern[r_sub][c_sub]
        scores, paths_by_player, fields_by_player, source_tiles = [0, 0], {1: [], 2: []}, {1: [], 2: []}, []
        for r in range(4):
            for c in range(6):
                if self.board_data[r][c]:
                    tile_type, owner_id, _ = self.board_data[r][c]
                    if tile_type == 4: fields_by_player[owner_id].append((r, c))
                    elif tile_type == 1: source_tiles.append((r, c))
        for player_id in [1, 2]:
            player_score = 0
            for r_field, c_field in fields_by_player[player_id]:
                q, visited, parent = deque(), set(), {}
                r_start_abs, c_start_abs = r_field*7, c_field*7
                # *** 核心修正點：嚴格檢查四條邊界，禁止對角線跳躍 ***
                # 上邊界
                if r_field > 0:
                    for c_offset in range(7):
                        r_check, c_check = r_start_abs - 1, c_start_abs + c_offset
                        if master_grid[r_check][c_check] == 1:
                            if (r_check, c_check) not in visited: q.append((r_check, c_check)); visited.add((r_check, c_check))
                # 下邊界
                if r_field < 3:
                    for c_offset in range(7):
                        r_check, c_check = r_start_abs + 7, c_start_abs + c_offset
                        if master_grid[r_check][c_check] == 1:
                            if (r_check, c_check) not in visited: q.append((r_check, c_check)); visited.add((r_check, c_check))
                # 左邊界
                if c_field > 0:
                    for r_offset in range(7):
                        r_check, c_check = r_start_abs + r_offset, c_start_abs - 1
                        if master_grid[r_check][c_check] == 1:
                            if (r_check, c_check) not in visited: q.append((r_check, c_check)); visited.add((r_check, c_check))
                # 右邊界
                if c_field < 5:
                    for r_offset in range(7):
                        r_check, c_check = r_start_abs + r_offset, c_start_abs + 7
                        if master_grid[r_check][c_check] == 1:
                            if (r_check, c_check) not in visited: q.append((r_check, c_check)); visited.add((r_check, c_check))

                field_connected_sources_ends = {}
                while q:
                    r_curr, c_curr = q.popleft()
                    current_source_tile = None
                    for r_source, c_source in source_tiles:
                        if (r_source*7 <= r_curr < (r_source+1)*7 and c_source*7 <= c_curr < (c_source+1)*7): current_source_tile = (r_source, c_source); break
                    if current_source_tile and current_source_tile not in field_connected_sources_ends: field_connected_sources_ends[current_source_tile] = (r_curr, c_curr)
                    for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        r_next, c_next = r_curr + dr, c_curr + dc
                        if not (0 <= r_next < master_grid_rows and 0 <= c_next < master_grid_cols): continue
                        if (r_next, c_next) in visited or master_grid[r_next][c_next] == 0: continue
                        visited.add((r_next, c_next)); parent[(r_next, c_next)] = (r_curr, c_curr); q.append((r_next, c_next))
                for source_coord, end_node in field_connected_sources_ends.items():
                    path, p_node = [], end_node
                    while p_node in parent: path.append(p_node); p_node = parent[p_node]
                    path.append(p_node); path.reverse()
                    paths_by_player[player_id].append({'field': (r_field, c_field), 'source': source_coord, 'path': path})
                player_score += len(field_connected_sources_ends)
            scores[player_id - 1] = player_score
        all_networks = self.find_all_water_networks(master_grid, master_grid_rows, master_grid_cols)
        return master_grid, scores, paths_by_player, fields_by_player, source_tiles, all_networks

if __name__ == "__main__":
    root = tk.Tk()
    app = RiverGameGUI(root)
    root.mainloop()