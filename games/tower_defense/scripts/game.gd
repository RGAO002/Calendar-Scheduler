extends Node2D
## Tower Defense — Strategic defense with diverse enemies, boss waves, and tower upgrades.
##
## Answer questions to build/upgrade towers. Different enemy types (basic, fast,
## tank, healer, boss). Towers auto-shoot. Defend your castle!

# ── Config ──
var config: Dictionary = {}
var waves: Array = []
var current_wave: int = 0
var score: int = 0
var base_hp: int = 15
var game_active: bool = false
var game_over: bool = false
var victory: bool = false

# ── Path ──
var path_points: Array = [
	Vector2(0, 360),
	Vector2(200, 360),
	Vector2(200, 180),
	Vector2(500, 180),
	Vector2(500, 540),
	Vector2(800, 540),
	Vector2(800, 300),
	Vector2(1100, 300),
	Vector2(1100, 500),
	Vector2(1280, 500),
]

# ── Tower slots ──
var tower_slots: Array = [
	Vector2(300, 280),
	Vector2(400, 100),
	Vector2(350, 450),
	Vector2(600, 100),
	Vector2(600, 450),
	Vector2(700, 620),
	Vector2(900, 200),
	Vector2(950, 420),
]
var towers: Array = []
const TOWER_RANGE: float = 180.0
const TOWER_SHOOT_CD: float = 1.0

# ── Enemies ──
var enemies: Array = []
var enemy_spawn_timer: float = 0.0
var enemies_to_spawn: int = 0
var enemy_speed: float = 60.0
var spawn_queue: Array = []

# ── Projectiles ──
var projectiles: Array = []
const PROJ_SPEED: float = 450.0

# ── Particles ──
var particles: Array = []

# ── Question phase ──
var showing_question: bool = false
var shuffled_answers: Array = []
var answered: bool = false
var show_result: bool = false
var result_timer: float = 0.0
var result_correct: bool = false
var answer_speed: float = 0.0
var question_start_time: float = 0.0

# ── Wave state ──
var wave_active: bool = false
var between_waves: bool = true

# ── Power-ups ──
var active_powerup: String = ""
var powerup_timer: float = 0.0

# ── Animation ──
var anim_timer: float = 0.0

# ── Colors ──
const C_GRASS = Color(0.3, 0.55, 0.28)
const C_GRASS_DARK = Color(0.25, 0.48, 0.22)
const C_PATH = Color(0.6, 0.5, 0.35)
const C_PATH_BORDER = Color(0.45, 0.38, 0.25)
const C_TOWER_BASE = Color(0.5, 0.5, 0.6)
const C_TOWER_TOP = Color(0.3, 0.4, 0.8)
const C_TOWER_SLOT = Color(0.4, 0.4, 0.45, 0.4)
const C_ENEMY_BASIC = Color(0.85, 0.25, 0.2)
const C_ENEMY_FAST = Color(0.9, 0.7, 0.1)
const C_ENEMY_TANK = Color(0.5, 0.3, 0.6)
const C_ENEMY_HEALER = Color(0.2, 0.85, 0.4)
const C_ENEMY_BOSS = Color(0.9, 0.15, 0.1)
const C_HP_BG = Color(0.2, 0.1, 0.1)
const C_HP_BAR = Color(0.2, 0.9, 0.2)
const C_PROJ = Color(1.0, 0.8, 0.2)
const C_BASE = Color(0.3, 0.5, 0.9)
const C_TEXT = Color(1, 1, 1)
const C_QUESTION_BG = Color(0.1, 0.08, 0.15, 0.9)
const C_CORRECT = Color(0.2, 0.85, 0.3)
const C_WRONG = Color(0.85, 0.2, 0.2)
const C_GOLD = Color(1, 0.85, 0.2)
const C_ANSWER_BG = Color(0.2, 0.18, 0.3)


func _ready() -> void:
	_load_config()
	_start_game()


func _load_config() -> void:
	if OS.has_feature("web"):
		var js_config = JavaScriptBridge.eval("JSON.stringify(window.gameConfig || {})")
		if js_config and js_config != "{}":
			var json = JSON.new()
			json.parse(js_config)
			config = json.data
			waves = config.get("waves", [])
			return
	var file = FileAccess.open("res://config.json", FileAccess.READ)
	if file:
		var json = JSON.new()
		json.parse(file.get_as_text())
		config = json.data
		waves = config.get("waves", [])
		file.close()


func _start_game() -> void:
	current_wave = 0
	score = 0
	base_hp = 15
	game_active = true
	game_over = false
	victory = false
	towers.clear()
	enemies.clear()
	projectiles.clear()
	particles.clear()
	spawn_queue.clear()
	between_waves = true
	wave_active = false
	showing_question = true
	answered = false
	active_powerup = ""
	_prepare_question()


func _prepare_question() -> void:
	if current_wave >= waves.size():
		victory = true
		game_active = false
		return
	showing_question = true
	answered = false
	question_start_time = 0.0
	var wave = waves[current_wave]
	shuffled_answers = [wave["correct"]]
	for w in wave.get("wrong", []):
		shuffled_answers.append(w)
	for i in range(shuffled_answers.size() - 1, 0, -1):
		var j = randi() % (i + 1)
		var tmp = shuffled_answers[i]
		shuffled_answers[i] = shuffled_answers[j]
		shuffled_answers[j] = tmp


func _process(delta: float) -> void:
	anim_timer += delta

	if game_over or victory:
		if Input.is_action_just_pressed("next_wave"):
			_start_game()
		queue_redraw()
		return

	if show_result:
		result_timer -= delta
		if result_timer <= 0:
			show_result = false
			showing_question = false
			_start_wave()
		queue_redraw()
		return

	if showing_question:
		question_start_time += delta
		_handle_answer_input()
		queue_redraw()
		return

	if between_waves:
		if Input.is_action_just_pressed("next_wave"):
			_prepare_question()
		queue_redraw()
		return

	if wave_active:
		_update_wave(delta)

	if powerup_timer > 0:
		powerup_timer -= delta
		if powerup_timer <= 0:
			active_powerup = ""

	_update_particles(delta)
	queue_redraw()


func _handle_answer_input() -> void:
	var ans = -1
	if Input.is_action_just_pressed("answer_1"):
		ans = 0
	elif Input.is_action_just_pressed("answer_2"):
		ans = 1
	elif Input.is_action_just_pressed("answer_3"):
		ans = 2
	elif Input.is_action_just_pressed("answer_4"):
		ans = 3

	if ans >= 0 and ans < shuffled_answers.size():
		var wave = waves[current_wave]
		result_correct = shuffled_answers[ans] == wave["correct"]
		answer_speed = question_start_time
		if result_correct:
			score += 1
			_build_tower()
			if answer_speed < 3.0:
				active_powerup = "damage_boost"
				powerup_timer = 15.0
			elif answer_speed < 5.0:
				active_powerup = "range_boost"
				powerup_timer = 12.0
		show_result = true
		result_timer = 1.5


func _build_tower() -> void:
	var tower_type = "basic"
	var tower_count = towers.size()
	if tower_count >= 6:
		tower_type = "cannon"
	elif tower_count >= 4:
		tower_type = "sniper"
	elif tower_count >= 2:
		tower_type = "rapid"

	for slot in tower_slots:
		var occupied = false
		for t in towers:
			if t["pos"].distance_to(slot) < 20:
				occupied = true
				break
		if not occupied:
			towers.append({
				"pos": slot, "level": 1, "shoot_timer": 0.0,
				"target_idx": -1, "type": tower_type, "kills": 0,
			})
			for i in range(8):
				_spawn_particle(slot, C_GOLD)
			return
	if towers.size() > 0:
		var idx = randi() % towers.size()
		towers[idx]["level"] += 1
		for i in range(6):
			_spawn_particle(towers[idx]["pos"], C_CORRECT)


func _start_wave() -> void:
	var wave = waves[current_wave]
	var num_enemies = wave.get("enemies", 5)
	enemy_speed = wave.get("enemy_speed", 60)
	enemy_spawn_timer = 0.0
	wave_active = true
	between_waves = false

	spawn_queue.clear()
	for i in range(num_enemies):
		var etype = "basic"
		var ehp = 3
		var espeed = enemy_speed
		var difficulty = current_wave
		var roll = randf()

		if difficulty >= 4 and roll < 0.1:
			etype = "healer"; ehp = 2; espeed = enemy_speed * 0.7
		elif difficulty >= 3 and roll < 0.25:
			etype = "tank"; ehp = 8; espeed = enemy_speed * 0.5
		elif difficulty >= 1 and roll < 0.45:
			etype = "fast"; ehp = 1; espeed = enemy_speed * 1.8
		else:
			etype = "basic"; ehp = 3; espeed = enemy_speed

		spawn_queue.append({"type": etype, "hp": ehp, "speed": espeed, "special": "heal" if etype == "healer" else ""})

	if (current_wave + 1) % 3 == 0 and current_wave > 0:
		spawn_queue.append({"type": "boss", "hp": 15 + current_wave * 3, "speed": enemy_speed * 0.4, "special": "boss"})

	enemies_to_spawn = spawn_queue.size()


func _update_wave(delta: float) -> void:
	if spawn_queue.size() > 0:
		enemy_spawn_timer -= delta
		if enemy_spawn_timer <= 0:
			var info = spawn_queue.pop_front()
			enemies.append({
				"path_idx": 0, "path_t": 0.0, "hp": info["hp"], "max_hp": info["hp"],
				"speed": info["speed"], "alive": true, "pos": path_points[0],
				"type": info["type"], "special": info["special"],
				"anim": randf_range(0, TAU), "heal_timer": 3.0,
			})
			enemy_spawn_timer = 0.6

	for e in enemies:
		if not e["alive"]:
			continue
		e["anim"] += delta
		var idx = e["path_idx"]
		if idx >= path_points.size() - 1:
			var dmg = 3 if e["type"] == "boss" else 1
			base_hp -= dmg
			e["alive"] = false
			_spawn_particle(e["pos"], C_WRONG)
			if base_hp <= 0:
				game_over = true; game_active = false; return
			continue

		var from_pt = path_points[idx]
		var to_pt = path_points[idx + 1]
		var seg_len = from_pt.distance_to(to_pt)
		e["path_t"] += (e["speed"] / seg_len) * delta
		if e["path_t"] >= 1.0:
			e["path_t"] = 0.0; e["path_idx"] += 1
		var t_val = clampf(e["path_t"], 0, 1)
		var cur_idx = e["path_idx"]
		if cur_idx < path_points.size() - 1:
			e["pos"] = path_points[cur_idx].lerp(path_points[cur_idx + 1], t_val)

		if e["special"] == "heal":
			e["heal_timer"] -= delta
			if e["heal_timer"] <= 0:
				e["heal_timer"] = 3.0
				for other in enemies:
					if other != e and other["alive"] and e["pos"].distance_to(other["pos"]) < 120:
						other["hp"] = mini(other["hp"] + 1, other["max_hp"])
						_spawn_particle(other["pos"], C_ENEMY_HEALER)

	var dmg_mult = 2.0 if active_powerup == "damage_boost" else 1.0
	var range_mult = 1.3 if active_powerup == "range_boost" else 1.0

	for t in towers:
		t["shoot_timer"] -= delta
		if t["shoot_timer"] <= 0:
			var effective_range = TOWER_RANGE * range_mult
			if t["type"] == "sniper":
				effective_range *= 1.5
			var best_dist = effective_range
			var best_enemy = null
			for e in enemies:
				if not e["alive"]:
					continue
				var d = t["pos"].distance_to(e["pos"])
				if d < effective_range and e["type"] == "boss":
					best_dist = d; best_enemy = e; break
			if best_enemy == null:
				for e in enemies:
					if not e["alive"]:
						continue
					var d = t["pos"].distance_to(e["pos"])
					if d < best_dist:
						best_dist = d; best_enemy = e
			if best_enemy != null:
				var proj_dmg = t["level"] * dmg_mult
				if t["type"] == "cannon":
					proj_dmg *= 2
				elif t["type"] == "sniper":
					proj_dmg *= 1.5
				projectiles.append({"pos": Vector2(t["pos"]), "target": best_enemy, "damage": proj_dmg, "type": t["type"]})
				var cd = TOWER_SHOOT_CD / t["level"]
				if t["type"] == "rapid":
					cd *= 0.5
				elif t["type"] == "cannon":
					cd *= 1.5
				t["shoot_timer"] = cd

	var new_projs: Array = []
	for p in projectiles:
		var target = p["target"]
		if target == null or not target["alive"]:
			continue
		var dir = (target["pos"] - p["pos"]).normalized()
		p["pos"] += dir * PROJ_SPEED * delta
		if p["pos"].distance_to(target["pos"]) < 15:
			target["hp"] -= p["damage"]
			_spawn_particle(target["pos"], C_PROJ)
			if target["hp"] <= 0:
				target["alive"] = false
				score += 2 if target["type"] == "boss" else 1
				var col = _get_enemy_color(target["type"])
				for i in range(8):
					_spawn_particle(target["pos"], col)
		else:
			new_projs.append(p)
	projectiles = new_projs

	var alive_count = 0
	for e in enemies:
		if e["alive"]:
			alive_count += 1
	if spawn_queue.size() == 0 and alive_count == 0:
		wave_active = false; between_waves = true; current_wave += 1
		if current_wave >= waves.size():
			victory = true; game_active = false


func _spawn_particle(pos: Vector2, col: Color) -> void:
	particles.append({"pos": Vector2(pos), "vel": Vector2(randf_range(-80, 80), randf_range(-80, 80)), "color": col, "life": randf_range(0.3, 0.6), "max_life": 0.6, "size": randf_range(2, 4)})


func _update_particles(delta: float) -> void:
	var new_p: Array = []
	for p in particles:
		p["life"] -= delta
		if p["life"] > 0:
			p["pos"] += p["vel"] * delta; p["vel"].y += 50 * delta; new_p.append(p)
	particles = new_p


func _get_enemy_color(etype: String) -> Color:
	match etype:
		"basic": return C_ENEMY_BASIC
		"fast": return C_ENEMY_FAST
		"tank": return C_ENEMY_TANK
		"healer": return C_ENEMY_HEALER
		"boss": return C_ENEMY_BOSS
	return C_ENEMY_BASIC


func _draw() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), C_GRASS)
	for ix in range(0, 1280, 64):
		for iy in range(0, 720, 64):
			if (ix + iy) % 128 == 0:
				draw_rect(Rect2(ix, iy, 64, 64), C_GRASS_DARK)
	_draw_scenery()
	_draw_path()
	for slot in tower_slots:
		var occupied = false
		for t in towers:
			if t["pos"].distance_to(slot) < 20:
				occupied = true; break
		if not occupied:
			draw_circle(slot, 22, C_TOWER_SLOT)
			draw_line(Vector2(slot.x - 8, slot.y), Vector2(slot.x + 8, slot.y), Color(1, 1, 1, 0.2), 2)
			draw_line(Vector2(slot.x, slot.y - 8), Vector2(slot.x, slot.y + 8), Color(1, 1, 1, 0.2), 2)
	for t in towers:
		_draw_tower(t)
	for e in enemies:
		if e["alive"]:
			_draw_enemy(e)
	for p in projectiles:
		if p["type"] == "cannon":
			draw_circle(p["pos"], 7, Color(1.0, 0.4, 0.1)); draw_circle(p["pos"], 4, Color(1, 0.8, 0.3))
		elif p["type"] == "sniper":
			draw_circle(p["pos"], 3, Color(0.3, 0.8, 1.0))
		else:
			draw_circle(p["pos"], 5, C_PROJ); draw_circle(p["pos"], 3, Color(1, 1, 0.8))
	for p in particles:
		var alpha = p["life"] / p["max_life"]
		draw_circle(p["pos"], p["size"] * alpha, Color(p["color"].r, p["color"].g, p["color"].b, alpha))
	_draw_base()
	_draw_hud()
	if showing_question:
		_draw_question()
	if show_result:
		_draw_result()
	if between_waves and not showing_question and not show_result and not victory and not game_over:
		_draw_between_waves()
	if game_over:
		_draw_game_over()
	if victory:
		_draw_victory()


func _draw_scenery() -> void:
	var tree_positions = [Vector2(50, 100), Vector2(80, 550), Vector2(1200, 100), Vector2(150, 650), Vector2(1100, 650), Vector2(650, 650)]
	for tp in tree_positions:
		draw_rect(Rect2(tp.x - 4, tp.y - 5, 8, 20), Color(0.4, 0.28, 0.15))
		draw_circle(Vector2(tp.x, tp.y - 12), 16, Color(0.2, 0.45, 0.2))
		draw_circle(Vector2(tp.x - 8, tp.y - 8), 10, Color(0.22, 0.5, 0.22))
		draw_circle(Vector2(tp.x + 8, tp.y - 8), 10, Color(0.18, 0.42, 0.18))


func _draw_path() -> void:
	for i in range(path_points.size() - 1):
		draw_line(path_points[i], path_points[i + 1], C_PATH_BORDER, 38)
		draw_line(path_points[i], path_points[i + 1], C_PATH, 30)
		var mid = (path_points[i] + path_points[i + 1]) / 2
		draw_circle(mid, 3, Color(0.5, 0.42, 0.3, 0.3))


func _draw_tower(t: Dictionary) -> void:
	var pos = t["pos"]; var lvl = t["level"]
	var range_val = TOWER_RANGE
	if t["type"] == "sniper":
		range_val *= 1.5
	if active_powerup == "range_boost":
		range_val *= 1.3
	_draw_circle_outline(pos, range_val, Color(0.5, 0.5, 0.8, 0.08))
	draw_circle(pos, 22, Color(0.4, 0.4, 0.45))
	match t["type"]:
		"basic":
			draw_rect(Rect2(pos.x - 14, pos.y - 14, 28, 28), C_TOWER_BASE)
			draw_rect(Rect2(pos.x - 8, pos.y - 22, 16, 10), C_TOWER_TOP)
		"rapid":
			draw_rect(Rect2(pos.x - 12, pos.y - 12, 24, 24), Color(0.3, 0.6, 0.3))
			draw_rect(Rect2(pos.x - 6, pos.y - 22, 4, 12), Color(0.25, 0.5, 0.25))
			draw_rect(Rect2(pos.x + 2, pos.y - 22, 4, 12), Color(0.25, 0.5, 0.25))
		"sniper":
			draw_rect(Rect2(pos.x - 10, pos.y - 10, 20, 20), Color(0.3, 0.4, 0.6))
			draw_rect(Rect2(pos.x - 2, pos.y - 28, 4, 20), Color(0.2, 0.3, 0.5))
			draw_circle(Vector2(pos.x, pos.y - 28), 4, Color(0.3, 0.6, 1.0))
		"cannon":
			draw_rect(Rect2(pos.x - 16, pos.y - 16, 32, 32), Color(0.5, 0.3, 0.2))
			draw_rect(Rect2(pos.x - 5, pos.y - 24, 10, 14), Color(0.4, 0.25, 0.15))
			draw_circle(Vector2(pos.x, pos.y - 24), 6, Color(0.6, 0.3, 0.1))
	for i in range(lvl):
		draw_circle(Vector2(pos.x - 8 + i * 6, pos.y + 18), 2.5, C_GOLD)
	if active_powerup == "damage_boost":
		draw_circle(pos, 18, Color(1, 0.5, 0, 0.15))


func _draw_enemy(e: Dictionary) -> void:
	var pos = e["pos"]; var bob = sin(e["anim"] * 4) * 2
	match e["type"]:
		"basic":
			draw_circle(Vector2(pos.x, pos.y + bob), 12, C_ENEMY_BASIC)
			draw_circle(Vector2(pos.x - 4, pos.y - 3 + bob), 3, Color.WHITE)
			draw_circle(Vector2(pos.x + 4, pos.y - 3 + bob), 3, Color.WHITE)
			draw_circle(Vector2(pos.x - 3, pos.y - 3 + bob), 1.5, Color.BLACK)
			draw_circle(Vector2(pos.x + 5, pos.y - 3 + bob), 1.5, Color.BLACK)
		"fast":
			var pts = PackedVector2Array([Vector2(pos.x, pos.y - 10 + bob), Vector2(pos.x - 8, pos.y + 8 + bob), Vector2(pos.x + 8, pos.y + 8 + bob)])
			draw_colored_polygon(pts, C_ENEMY_FAST)
			draw_circle(Vector2(pos.x, pos.y - 2 + bob), 3, Color.WHITE)
			draw_circle(Vector2(pos.x, pos.y - 2 + bob), 1.5, Color.BLACK)
			draw_line(Vector2(pos.x - 15, pos.y + bob), Vector2(pos.x - 22, pos.y + bob), Color(1, 0.8, 0.2, 0.4), 1)
		"tank":
			draw_rect(Rect2(pos.x - 16, pos.y - 14 + bob, 32, 28), C_ENEMY_TANK)
			draw_rect(Rect2(pos.x - 12, pos.y - 10 + bob, 24, 20), Color(0.6, 0.4, 0.7))
			draw_line(Vector2(pos.x - 8, pos.y - 8 + bob), Vector2(pos.x - 2, pos.y - 4 + bob), Color.WHITE, 3)
			draw_line(Vector2(pos.x + 8, pos.y - 8 + bob), Vector2(pos.x + 2, pos.y - 4 + bob), Color.WHITE, 3)
		"healer":
			draw_circle(Vector2(pos.x, pos.y + bob), 10, C_ENEMY_HEALER)
			draw_rect(Rect2(pos.x - 2, pos.y - 6 + bob, 4, 12), Color.WHITE)
			draw_rect(Rect2(pos.x - 6, pos.y - 2 + bob, 12, 4), Color.WHITE)
			draw_circle(Vector2(pos.x, pos.y + bob), 18, Color(0.2, 0.85, 0.4, 0.1 + sin(e["anim"] * 3) * 0.05))
		"boss":
			draw_circle(Vector2(pos.x, pos.y + bob), 22, C_ENEMY_BOSS)
			draw_circle(Vector2(pos.x, pos.y + bob), 18, Color(0.7, 0.1, 0.05))
			var crown = PackedVector2Array([Vector2(pos.x - 14, pos.y - 18 + bob), Vector2(pos.x - 10, pos.y - 28 + bob), Vector2(pos.x - 5, pos.y - 22 + bob), Vector2(pos.x, pos.y - 30 + bob), Vector2(pos.x + 5, pos.y - 22 + bob), Vector2(pos.x + 10, pos.y - 28 + bob), Vector2(pos.x + 14, pos.y - 18 + bob)])
			draw_colored_polygon(crown, C_GOLD)
			draw_circle(Vector2(pos.x - 6, pos.y - 4 + bob), 5, Color(1, 1, 0))
			draw_circle(Vector2(pos.x + 6, pos.y - 4 + bob), 5, Color(1, 1, 0))
			draw_circle(Vector2(pos.x - 5, pos.y - 4 + bob), 2.5, Color.BLACK)
			draw_circle(Vector2(pos.x + 7, pos.y - 4 + bob), 2.5, Color.BLACK)
	var bar_w = 24.0 if e["type"] != "boss" else 40.0
	var bar_y = -20.0 if e["type"] != "boss" else -35.0
	draw_rect(Rect2(pos.x - bar_w / 2, pos.y + bar_y, bar_w, 4), C_HP_BG)
	var hp_ratio = float(e["hp"]) / e["max_hp"]
	draw_rect(Rect2(pos.x - bar_w / 2, pos.y + bar_y, bar_w * hp_ratio, 4), C_HP_BAR)


func _draw_base() -> void:
	var bx = 1230.0; var by = 500.0
	draw_rect(Rect2(bx - 35, by - 45, 70, 90), C_BASE)
	for i in range(5):
		draw_rect(Rect2(bx - 35 + i * 15, by - 55, 10, 14), C_BASE)
	draw_rect(Rect2(bx - 12, by + 10, 24, 35), Color(0.2, 0.35, 0.7))
	draw_line(Vector2(bx, by - 55), Vector2(bx, by - 75), Color(0.5, 0.4, 0.3), 2)
	var flag_pts = PackedVector2Array([Vector2(bx, by - 75), Vector2(bx + 18, by - 68), Vector2(bx, by - 61)])
	draw_colored_polygon(flag_pts, Color(0.9, 0.2, 0.2))
	var font = ThemeDB.fallback_font
	var hp_col = C_CORRECT if base_hp > 8 else C_GOLD if base_hp > 4 else C_WRONG
	draw_string(font, Vector2(bx - 25, by + 65), "HP:" + str(base_hp), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, hp_col)


func _draw_hud() -> void:
	var font = ThemeDB.fallback_font
	draw_rect(Rect2(0, 0, 1280, 40), Color(0, 0, 0, 0.5))
	draw_string(font, Vector2(20, 28), config.get("title", "Tower Defense"), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_GOLD)
	draw_string(font, Vector2(400, 28), "Wave: " + str(current_wave + 1) + "/" + str(waves.size()), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_TEXT)
	draw_string(font, Vector2(580, 28), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_TEXT)
	draw_string(font, Vector2(730, 28), "Towers: " + str(towers.size()), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_TEXT)
	draw_string(font, Vector2(900, 28), "Base HP: " + str(base_hp), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_CORRECT if base_hp > 8 else C_GOLD if base_hp > 4 else C_WRONG)
	if active_powerup != "":
		var pu_text = active_powerup.replace("_", " ").to_upper() + " " + str(int(powerup_timer)) + "s"
		draw_string(font, Vector2(1080, 28), pu_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 0.5, 0))
	if wave_active:
		var alive = 0
		for e in enemies:
			if e["alive"]:
				alive += 1
		draw_string(font, Vector2(20, 710), "Enemies: " + str(alive), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_TEXT)


func _draw_question() -> void:
	if current_wave >= waves.size():
		return
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.5))
	var panel_x = 250.0; var panel_y = 150.0; var panel_w = 780.0; var panel_h = 420.0
	draw_rect(Rect2(panel_x, panel_y, panel_w, panel_h), C_QUESTION_BG)
	draw_rect(Rect2(panel_x, panel_y, panel_w, 4), C_GOLD)
	var font = ThemeDB.fallback_font; var wave = waves[current_wave]
	draw_string(font, Vector2(panel_x + 20, panel_y + 35), "Wave " + str(current_wave + 1) + " — Answer to build a tower!", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_GOLD)
	draw_string(font, Vector2(panel_x + panel_w - 200, panel_y + 35), "Fast answer = bonus!", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.6, 0.8, 1.0))
	var q_text = wave.get("question", "")
	var q_w = font.get_string_size(q_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - q_w / 2, panel_y + 80), q_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	for i in range(shuffled_answers.size()):
		var ax = panel_x + 40; var ay = panel_y + 110 + i * 65; var aw = panel_w - 80; var ah = 50
		draw_rect(Rect2(ax, ay, aw, ah), C_ANSWER_BG)
		draw_rect(Rect2(ax, ay, 40, ah), Color(0.35, 0.3, 0.55))
		draw_string(font, Vector2(ax + 13, ay + 32), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)
		draw_string(font, Vector2(ax + 55, ay + 32), shuffled_answers[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_TEXT)


func _draw_result() -> void:
	var font = ThemeDB.fallback_font
	var text: String; var col: Color
	if result_correct:
		text = "CORRECT! Tower built!"
		if answer_speed < 3.0:
			text += " +DAMAGE BOOST!"
		elif answer_speed < 5.0:
			text += " +RANGE BOOST!"
		col = C_CORRECT
	else:
		text = "WRONG! No tower this wave."; col = C_WRONG
	draw_rect(Rect2(250, 340, 780, 60), Color(0, 0, 0, 0.8))
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw / 2, 378), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, col)


func _draw_between_waves() -> void:
	var font = ThemeDB.fallback_font
	var text = "Wave " + str(current_wave) + " cleared! Press SPACE for next wave"
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_rect(Rect2(300, 340, 680, 50), Color(0, 0, 0, 0.7))
	draw_string(font, Vector2(640 - tw / 2, 372), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_GOLD)


func _draw_game_over() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.7))
	var font = ThemeDB.fallback_font
	var t1 = "BASE DESTROYED!"; var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 280), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_WRONG)
	var t2 = "Waves survived: " + str(current_wave) + "/" + str(waves.size()); var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 340), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	draw_string(font, Vector2(640 - 30, 380), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_GOLD)
	draw_string(font, Vector2(640 - 80, 430), "Press SPACE to retry", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _draw_victory() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.6))
	var font = ThemeDB.fallback_font
	var t1 = "FORTRESS DEFENDED!"; var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 240), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_CORRECT)
	var t2 = "Score: " + str(score) + " | Base HP: " + str(base_hp) + "/15"; var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 310), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	var num_stars = 3 if base_hp >= 12 else 2 if base_hp >= 8 else 1 if base_hp >= 3 else 0
	var star_text = ""
	for i in range(num_stars):
		star_text += "★ "
	for i in range(3 - num_stars):
		star_text += "☆ "
	var tw3 = font.get_string_size(star_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 40).x
	draw_string(font, Vector2(640 - tw3 / 2, 375), star_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 40, C_GOLD)
	draw_string(font, Vector2(640 - 130, 420), "Towers: " + str(towers.size()) + " | Defeated: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0.7, 0.8, 1))
	draw_string(font, Vector2(640 - 95, 470), "Press SPACE to play again", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _draw_circle_outline(center: Vector2, radius: float, color: Color) -> void:
	var pts = 32
	for i in range(pts):
		var a1 = i * TAU / pts; var a2 = (i + 1) * TAU / pts
		draw_line(center + Vector2(cos(a1), sin(a1)) * radius, center + Vector2(cos(a2), sin(a2)) * radius, color, 1.0)
