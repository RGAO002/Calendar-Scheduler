extends Node2D
## Quiz Dungeon — Top-down dungeon crawler RPG with REAL combat.
##
## Each room: fight enemies (WASD move, SPACE attack), then answer the door
## question to proceed. Equipment from rewards affects your stats!

# ── Config ──
var config: Dictionary = {}
var rooms: Array = []
var current_room: int = 0
var score: int = 0

# ── Player stats ──
var hp: int = 8
var max_hp: int = 8
var atk: int = 1
var defense: int = 0
var speed_bonus: float = 0.0

# ── Game state ──
var game_active: bool = false
var game_over: bool = false
var victory: bool = false
var showing_question: bool = false
var show_result: bool = false
var result_timer: float = 0.0
var result_correct: bool = false
var door_unlocked: bool = false
var enemies_cleared: bool = false
var room_transition: float = 0.0  # fade effect

# ── Player ──
var player_pos: Vector2 = Vector2(640, 500)
const PLAYER_SPEED: float = 220.0
const PLAYER_SIZE: float = 28.0
var player_dir: int = 0  # 0=down, 1=up, 2=left, 3=right
var walk_timer: float = 0.0
var is_walking: bool = false
var attack_timer: float = 0.0
var attack_cooldown: float = 0.0
const ATTACK_RANGE: float = 60.0
const ATTACK_DURATION: float = 0.25
var invincible_timer: float = 0.0
var inventory: Array = []  # reward names
var inventory_types: Array = []  # reward types (sword/shield/potion/helmet/boots)

# ── Enemies ──
var enemies: Array = []
# Each: {pos, hp, max_hp, type, speed, dir, state, timer, damage, alive, hit_flash}
# type: "slime", "bat", "skeleton"

# ── Pickups (from killed enemies) ──
var pickups: Array = []  # {pos, type, timer}  type: "coin", "heart"

# ── Particles ──
var particles: Array = []  # {pos, vel, color, life, max_life, size}

# ── Door ──
var door_rect: Rect2 = Rect2(570, 100, 140, 60)

# ── Room visuals ──
const ROOM_X: float = 100.0
const ROOM_Y: float = 80.0
const ROOM_W: float = 1080.0
const ROOM_H: float = 560.0

# ── Decorations (generated per room) ──
var decorations: Array = []  # {pos, type}  type: "crate", "barrel", "bones", "crack"

# ── Answer choices ──
var shuffled_answers: Array = []

# ── Torch flicker ──
var torch_timer: float = 0.0

# ── Colors ──
const C_FLOOR = Color(0.22, 0.18, 0.16)
const C_FLOOR_TILE = Color(0.25, 0.21, 0.18)
const C_WALL = Color(0.35, 0.3, 0.25)
const C_WALL_DARK = Color(0.18, 0.15, 0.12)
const C_DOOR_LOCKED = Color(0.55, 0.28, 0.12)
const C_DOOR_OPEN = Color(0.15, 0.5, 0.2)
const C_DOOR_INACTIVE = Color(0.4, 0.35, 0.3)
const C_PLAYER_BODY = Color(0.3, 0.5, 0.9)
const C_PLAYER_HEAD = Color(1.0, 0.85, 0.7)
const C_TORCH = Color(1.0, 0.7, 0.2)
const C_HP = Color(0.85, 0.15, 0.15)
const C_HP_BG = Color(0.3, 0.1, 0.1)
const C_TEXT = Color(1, 1, 1)
const C_QUESTION_BG = Color(0.1, 0.08, 0.15, 0.92)
const C_ANSWER_BG = Color(0.2, 0.18, 0.3)
const C_CORRECT = Color(0.2, 0.85, 0.3)
const C_WRONG = Color(0.85, 0.2, 0.2)
const C_GOLD = Color(1.0, 0.85, 0.2)
const C_REWARD = Color(0.4, 0.8, 1.0)
const C_SLIME = Color(0.3, 0.8, 0.3)
const C_BAT = Color(0.5, 0.3, 0.6)
const C_SKELETON = Color(0.85, 0.82, 0.75)
const C_COIN = Color(1.0, 0.85, 0.1)
const C_HEART = Color(1.0, 0.3, 0.4)
const C_SWORD_SWING = Color(0.9, 0.9, 1.0, 0.6)


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
			rooms = config.get("rooms", [])
			return
	var file = FileAccess.open("res://config.json", FileAccess.READ)
	if file:
		var json = JSON.new()
		json.parse(file.get_as_text())
		config = json.data
		rooms = config.get("rooms", [])
		file.close()


func _start_game() -> void:
	current_room = 0
	score = 0
	hp = 8
	max_hp = 8
	atk = 1
	defense = 0
	speed_bonus = 0.0
	inventory.clear()
	inventory_types.clear()
	game_active = true
	game_over = false
	victory = false
	showing_question = false
	door_unlocked = false
	enemies_cleared = false
	player_pos = Vector2(640, 500)
	enemies.clear()
	pickups.clear()
	particles.clear()
	_setup_room()
	queue_redraw()


func _setup_room() -> void:
	enemies.clear()
	pickups.clear()
	door_unlocked = false
	enemies_cleared = false
	room_transition = 0.5

	# Generate decorations
	decorations.clear()
	var deco_types = ["crate", "barrel", "bones", "crack"]
	var num_decos = randi_range(3, 6)
	for i in range(num_decos):
		var dx = randf_range(ROOM_X + 60, ROOM_X + ROOM_W - 60)
		var dy = randf_range(ROOM_Y + 100, ROOM_Y + ROOM_H - 60)
		# Avoid door area
		if dy < 200 and abs(dx - 640) < 120:
			continue
		decorations.append({"pos": Vector2(dx, dy), "type": deco_types[randi() % deco_types.size()]})

	# Spawn enemies based on room number
	var num_enemies = mini(2 + current_room, 6)
	for i in range(num_enemies):
		var etype: String
		var room_idx = current_room
		if room_idx < 2:
			etype = "slime"
		elif room_idx < 4:
			etype = ["slime", "bat"][randi() % 2]
		else:
			etype = ["slime", "bat", "skeleton"][randi() % 3]

		var ex = randf_range(ROOM_X + 80, ROOM_X + ROOM_W - 80)
		var ey = randf_range(ROOM_Y + 120, ROOM_Y + ROOM_H - 80)
		# Don't spawn on player
		while Vector2(ex, ey).distance_to(player_pos) < 120:
			ex = randf_range(ROOM_X + 80, ROOM_X + ROOM_W - 80)
			ey = randf_range(ROOM_Y + 120, ROOM_Y + ROOM_H - 80)

		var ehp = 2
		var espeed = 50.0
		var edmg = 1
		match etype:
			"slime":
				ehp = 2
				espeed = 40.0 + current_room * 5
				edmg = 1
			"bat":
				ehp = 1
				espeed = 80.0 + current_room * 5
				edmg = 1
			"skeleton":
				ehp = 4
				espeed = 35.0
				edmg = 2

		enemies.append({
			"pos": Vector2(ex, ey),
			"hp": ehp,
			"max_hp": ehp,
			"type": etype,
			"speed": espeed,
			"dir": Vector2(randf_range(-1, 1), randf_range(-1, 1)).normalized(),
			"state": "wander",  # wander, chase, hurt
			"timer": randf_range(0, 3),
			"damage": edmg,
			"alive": true,
			"hit_flash": 0.0,
			"anim_timer": randf_range(0, 10),
		})


func _process(delta: float) -> void:
	torch_timer += delta

	# Room transition fade
	if room_transition > 0:
		room_transition -= delta * 2
		queue_redraw()
		return

	if game_over or victory:
		if Input.is_action_just_pressed("interact"):
			_start_game()
		queue_redraw()
		return

	if show_result:
		result_timer -= delta
		if result_timer <= 0:
			show_result = false
			if result_correct:
				door_unlocked = true
				# Apply reward
				if current_room < rooms.size():
					var room = rooms[current_room]
					_apply_reward(room.get("reward", "potion"), room.get("reward_name", "Item"))
			showing_question = false
		queue_redraw()
		return

	if showing_question:
		_handle_answer_input()
		queue_redraw()
		return

	if not game_active:
		queue_redraw()
		return

	# Invincibility timer
	if invincible_timer > 0:
		invincible_timer -= delta

	# Attack cooldown
	if attack_cooldown > 0:
		attack_cooldown -= delta
	if attack_timer > 0:
		attack_timer -= delta

	# Player movement
	var move = Vector2.ZERO
	is_walking = false
	if Input.is_action_pressed("move_left"):
		move.x -= 1
		player_dir = 2
		is_walking = true
	if Input.is_action_pressed("move_right"):
		move.x += 1
		player_dir = 3
		is_walking = true
	if Input.is_action_pressed("move_up"):
		move.y -= 1
		player_dir = 1
		is_walking = true
	if Input.is_action_pressed("move_down"):
		move.y += 1
		player_dir = 0
		is_walking = true

	if move != Vector2.ZERO:
		move = move.normalized()
		var spd = PLAYER_SPEED + speed_bonus
		var new_pos = player_pos + move * spd * delta
		new_pos.x = clampf(new_pos.x, ROOM_X + 40, ROOM_X + ROOM_W - 40)
		new_pos.y = clampf(new_pos.y, ROOM_Y + 40, ROOM_Y + ROOM_H - 40)

		# Block at door if not enemies cleared or door locked
		if not door_unlocked and new_pos.y < door_rect.position.y + door_rect.size.y + 30:
			if abs(new_pos.x - (door_rect.position.x + door_rect.size.x / 2)) < door_rect.size.x / 2 + 20:
				new_pos.y = door_rect.position.y + door_rect.size.y + 30

		player_pos = new_pos
		walk_timer += delta * 8

	# Attack
	if Input.is_action_just_pressed("interact") and attack_cooldown <= 0:
		if not enemies_cleared:
			_player_attack()
		else:
			# Check door interaction
			var door_center = door_rect.position + door_rect.size / 2
			if player_pos.distance_to(door_center) < 120:
				if door_unlocked:
					_enter_next_room()
				else:
					_show_question()

	# Update enemies
	_update_enemies(delta)

	# Check if all enemies dead
	if not enemies_cleared:
		var all_dead = true
		for e in enemies:
			if e["alive"]:
				all_dead = false
				break
		if all_dead:
			enemies_cleared = true
			# Fanfare particles
			for i in range(20):
				_spawn_particle(Vector2(640, 360), Color(1, 0.85, 0.2), 3.0)

	# Update pickups
	_update_pickups(delta)

	# Update particles
	_update_particles(delta)

	# Enemy collision damage
	if invincible_timer <= 0:
		for e in enemies:
			if not e["alive"]:
				continue
			if player_pos.distance_to(e["pos"]) < PLAYER_SIZE + 15:
				var dmg = maxi(e["damage"] - defense, 1)
				hp -= dmg
				invincible_timer = 1.0
				# Knockback
				var kb = (player_pos - e["pos"]).normalized() * 80
				player_pos += kb
				player_pos.x = clampf(player_pos.x, ROOM_X + 40, ROOM_X + ROOM_W - 40)
				player_pos.y = clampf(player_pos.y, ROOM_Y + 40, ROOM_Y + ROOM_H - 40)
				# Damage particles
				for i in range(5):
					_spawn_particle(player_pos, C_WRONG, 2.0)
				if hp <= 0:
					game_over = true
					game_active = false
					return

	queue_redraw()


func _player_attack() -> void:
	attack_timer = ATTACK_DURATION
	attack_cooldown = 0.35

	# Check hit enemies
	var attack_dir = Vector2.ZERO
	match player_dir:
		0: attack_dir = Vector2(0, 1)
		1: attack_dir = Vector2(0, -1)
		2: attack_dir = Vector2(-1, 0)
		3: attack_dir = Vector2(1, 0)

	var hit_pos = player_pos + attack_dir * 35

	for e in enemies:
		if not e["alive"]:
			continue
		if hit_pos.distance_to(e["pos"]) < ATTACK_RANGE:
			e["hp"] -= atk
			e["hit_flash"] = 0.2
			e["state"] = "hurt"
			e["timer"] = 0.3
			# Knockback enemy
			var kb_dir = (e["pos"] - player_pos).normalized()
			e["pos"] += kb_dir * 40
			e["pos"].x = clampf(e["pos"].x, ROOM_X + 30, ROOM_X + ROOM_W - 30)
			e["pos"].y = clampf(e["pos"].y, ROOM_Y + 30, ROOM_Y + ROOM_H - 30)

			# Hit particles
			for i in range(4):
				_spawn_particle(e["pos"], C_GOLD, 1.5)

			if e["hp"] <= 0:
				e["alive"] = false
				score += 1
				# Death particles
				var col = C_SLIME if e["type"] == "slime" else C_BAT if e["type"] == "bat" else C_SKELETON
				for i in range(12):
					_spawn_particle(e["pos"], col, 2.0)
				# Drop pickup
				if randf() < 0.5:
					var ptype = "coin" if randf() < 0.7 else "heart"
					pickups.append({"pos": e["pos"], "type": ptype, "timer": 8.0})


func _update_enemies(delta: float) -> void:
	for e in enemies:
		if not e["alive"]:
			continue

		e["anim_timer"] += delta
		e["hit_flash"] = maxf(e["hit_flash"] - delta, 0)

		match e["state"]:
			"hurt":
				e["timer"] -= delta
				if e["timer"] <= 0:
					e["state"] = "chase"
			"wander":
				e["timer"] -= delta
				e["pos"] += e["dir"] * e["speed"] * 0.5 * delta
				# Bounce off walls
				if e["pos"].x < ROOM_X + 30 or e["pos"].x > ROOM_X + ROOM_W - 30:
					e["dir"].x *= -1
				if e["pos"].y < ROOM_Y + 30 or e["pos"].y > ROOM_Y + ROOM_H - 30:
					e["dir"].y *= -1
				e["pos"].x = clampf(e["pos"].x, ROOM_X + 30, ROOM_X + ROOM_W - 30)
				e["pos"].y = clampf(e["pos"].y, ROOM_Y + 30, ROOM_Y + ROOM_H - 30)
				# Switch to chase if player nearby
				if player_pos.distance_to(e["pos"]) < 250:
					e["state"] = "chase"
				if e["timer"] <= 0:
					e["dir"] = Vector2(randf_range(-1, 1), randf_range(-1, 1)).normalized()
					e["timer"] = randf_range(1.5, 3.0)
			"chase":
				var chase_dir = (player_pos - e["pos"]).normalized()
				e["pos"] += chase_dir * e["speed"] * delta
				e["pos"].x = clampf(e["pos"].x, ROOM_X + 30, ROOM_X + ROOM_W - 30)
				e["pos"].y = clampf(e["pos"].y, ROOM_Y + 30, ROOM_Y + ROOM_H - 30)
				# Lose interest if far
				if player_pos.distance_to(e["pos"]) > 400:
					e["state"] = "wander"
					e["timer"] = randf_range(1.0, 2.0)


func _update_pickups(delta: float) -> void:
	var new_pickups: Array = []
	for p in pickups:
		p["timer"] -= delta
		if p["timer"] <= 0:
			continue
		# Check collection
		if player_pos.distance_to(p["pos"]) < 30:
			if p["type"] == "coin":
				score += 1
				_spawn_particle(p["pos"], C_COIN, 1.0)
			elif p["type"] == "heart":
				hp = mini(hp + 1, max_hp)
				for i in range(5):
					_spawn_particle(p["pos"], C_HEART, 1.5)
			continue
		new_pickups.append(p)
	pickups = new_pickups


func _spawn_particle(pos: Vector2, col: Color, size: float) -> void:
	particles.append({
		"pos": pos,
		"vel": Vector2(randf_range(-80, 80), randf_range(-80, 80)),
		"color": col,
		"life": randf_range(0.3, 0.6),
		"max_life": 0.6,
		"size": size,
	})


func _update_particles(delta: float) -> void:
	var new_parts: Array = []
	for p in particles:
		p["life"] -= delta
		if p["life"] > 0:
			p["pos"] += p["vel"] * delta
			p["vel"].y += 100 * delta  # gravity
			new_parts.append(p)
	particles = new_parts


func _apply_reward(reward_type: String, reward_name: String) -> void:
	inventory.append(reward_name)
	inventory_types.append(reward_type)
	match reward_type:
		"sword":
			atk += 1
		"shield":
			defense += 1
		"potion":
			hp = mini(hp + 3, max_hp)
		"helmet":
			max_hp += 2
			hp += 2
		"boots":
			speed_bonus += 30.0


func _show_question() -> void:
	if current_room >= rooms.size():
		return
	showing_question = true
	var room = rooms[current_room]
	shuffled_answers = [room["correct"]]
	for w in room.get("wrong", []):
		shuffled_answers.append(w)
	for i in range(shuffled_answers.size() - 1, 0, -1):
		var j = randi() % (i + 1)
		var tmp = shuffled_answers[i]
		shuffled_answers[i] = shuffled_answers[j]
		shuffled_answers[j] = tmp


func _handle_answer_input() -> void:
	var answered = -1
	if Input.is_action_just_pressed("answer_1"):
		answered = 0
	elif Input.is_action_just_pressed("answer_2"):
		answered = 1
	elif Input.is_action_just_pressed("answer_3"):
		answered = 2
	elif Input.is_action_just_pressed("answer_4"):
		answered = 3

	if answered >= 0 and answered < shuffled_answers.size():
		var room = rooms[current_room]
		if shuffled_answers[answered] == room["correct"]:
			score += 5
			result_correct = true
		else:
			hp -= 1
			result_correct = false
			if hp <= 0:
				game_over = true
				game_active = false
				showing_question = false
				return
		show_result = true
		result_timer = 1.5


func _enter_next_room() -> void:
	current_room += 1
	player_pos = Vector2(640, 500)
	if current_room >= rooms.size():
		victory = true
		game_active = false
	else:
		_setup_room()


# ══════════════════════════════════════════════════
# DRAWING
# ══════════════════════════════════════════════════

func _draw() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0.05, 0.04, 0.08))

	if game_over:
		_draw_game_over()
		return
	if victory:
		_draw_victory()
		return

	_draw_room()
	_draw_decorations()
	_draw_door()
	_draw_torches()
	_draw_pickups()
	_draw_enemies()
	_draw_player()
	_draw_particles()
	_draw_hud()

	if showing_question:
		_draw_question()
	if show_result:
		_draw_result()

	# Room transition overlay
	if room_transition > 0:
		draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, room_transition * 2))

	# Enemies remaining indicator
	if not enemies_cleared:
		var alive_count = 0
		for e in enemies:
			if e["alive"]:
				alive_count += 1
		var font = ThemeDB.fallback_font
		var et = str(alive_count) + " enemies remaining"
		draw_string(font, Vector2(ROOM_X + ROOM_W - 200, ROOM_Y + ROOM_H - 10), et, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_WRONG)
	elif not door_unlocked:
		var font = ThemeDB.fallback_font
		draw_string(font, Vector2(ROOM_X + ROOM_W - 240, ROOM_Y + ROOM_H - 10), "All clear! Approach the door", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_CORRECT)


func _draw_room() -> void:
	draw_rect(Rect2(ROOM_X - 20, ROOM_Y - 20, ROOM_W + 40, ROOM_H + 40), C_WALL_DARK)
	draw_rect(Rect2(ROOM_X - 10, ROOM_Y - 10, ROOM_W + 20, ROOM_H + 20), C_WALL)
	draw_rect(Rect2(ROOM_X, ROOM_Y, ROOM_W, ROOM_H), C_FLOOR)

	# Floor tiles with subtle variation
	for ix in range(0, int(ROOM_W), 80):
		for iy in range(0, int(ROOM_H), 80):
			var tx = ROOM_X + ix
			var ty = ROOM_Y + iy
			var shade = 0.02 * sin(float(ix) * 0.5 + float(iy) * 0.3)
			draw_rect(Rect2(tx + 1, ty + 1, 78, 78), Color(C_FLOOR_TILE.r + shade, C_FLOOR_TILE.g + shade, C_FLOOR_TILE.b + shade))

	var font = ThemeDB.fallback_font
	var room_text = "Room " + str(current_room + 1) + "/" + str(rooms.size())
	draw_string(font, Vector2(ROOM_X + 10, ROOM_Y + ROOM_H - 10), room_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(0.5, 0.45, 0.4))


func _draw_decorations() -> void:
	for d in decorations:
		var p = d["pos"]
		match d["type"]:
			"crate":
				draw_rect(Rect2(p.x - 14, p.y - 14, 28, 28), Color(0.5, 0.35, 0.2))
				draw_rect(Rect2(p.x - 12, p.y - 12, 24, 24), Color(0.6, 0.45, 0.25))
				draw_line(Vector2(p.x - 12, p.y), Vector2(p.x + 12, p.y), Color(0.45, 0.3, 0.15), 2)
				draw_line(Vector2(p.x, p.y - 12), Vector2(p.x, p.y + 12), Color(0.45, 0.3, 0.15), 2)
			"barrel":
				_draw_ellipse_shape(Rect2(p.x - 12, p.y - 16, 24, 32), Color(0.5, 0.35, 0.2))
				draw_line(Vector2(p.x - 12, p.y - 6), Vector2(p.x + 12, p.y - 6), Color(0.4, 0.28, 0.15), 2)
				draw_line(Vector2(p.x - 12, p.y + 6), Vector2(p.x + 12, p.y + 6), Color(0.4, 0.28, 0.15), 2)
			"bones":
				draw_line(Vector2(p.x - 8, p.y - 5), Vector2(p.x + 8, p.y + 5), Color(0.7, 0.68, 0.6), 2)
				draw_line(Vector2(p.x + 8, p.y - 5), Vector2(p.x - 8, p.y + 5), Color(0.7, 0.68, 0.6), 2)
				draw_circle(p, 3, Color(0.7, 0.68, 0.6))
			"crack":
				draw_line(Vector2(p.x - 10, p.y), Vector2(p.x, p.y - 8), Color(0.15, 0.12, 0.1), 1.5)
				draw_line(Vector2(p.x, p.y - 8), Vector2(p.x + 6, p.y + 3), Color(0.15, 0.12, 0.1), 1.5)
				draw_line(Vector2(p.x, p.y - 8), Vector2(p.x - 4, p.y + 10), Color(0.15, 0.12, 0.1), 1.5)


func _draw_door() -> void:
	var col: Color
	if enemies_cleared:
		col = C_DOOR_OPEN if door_unlocked else C_DOOR_LOCKED
	else:
		col = C_DOOR_INACTIVE

	draw_rect(Rect2(door_rect.position.x - 10, door_rect.position.y - 10,
		door_rect.size.x + 20, door_rect.size.y + 10), C_WALL)
	draw_rect(door_rect, col)

	var font = ThemeDB.fallback_font
	var door_center = door_rect.position + door_rect.size / 2

	if not enemies_cleared:
		# Skull icon on inactive door
		draw_circle(Vector2(door_center.x, door_center.y - 5), 10, Color(0.6, 0.55, 0.5))
		draw_circle(Vector2(door_center.x - 4, door_center.y - 7), 2, Color(0.2, 0.15, 0.1))
		draw_circle(Vector2(door_center.x + 4, door_center.y - 7), 2, Color(0.2, 0.15, 0.1))
	elif not door_unlocked:
		# Lock icon
		var lx = door_center.x
		var ly = door_center.y
		draw_circle(Vector2(lx, ly - 5), 12, C_GOLD)
		draw_circle(Vector2(lx, ly - 5), 7, col)
		draw_rect(Rect2(lx - 10, ly, 20, 15), C_GOLD)
		if player_pos.distance_to(door_center) < 120:
			draw_string(font, Vector2(door_rect.position.x - 10, door_rect.position.y - 20),
				"Press SPACE", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_GOLD)
	else:
		if player_pos.distance_to(door_center) < 120:
			draw_string(font, Vector2(door_rect.position.x - 5, door_rect.position.y - 20),
				"SPACE to enter", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_DOOR_OPEN)


func _draw_torches() -> void:
	var flicker = sin(torch_timer * 5) * 0.15 + 0.85
	var torch_positions = [
		Vector2(ROOM_X + 30, ROOM_Y + 30),
		Vector2(ROOM_X + ROOM_W - 30, ROOM_Y + 30),
		Vector2(ROOM_X + 30, ROOM_Y + ROOM_H - 30),
		Vector2(ROOM_X + ROOM_W - 30, ROOM_Y + ROOM_H - 30),
		Vector2(ROOM_X + ROOM_W / 2 - 200, ROOM_Y + 30),
		Vector2(ROOM_X + ROOM_W / 2 + 200, ROOM_Y + 30),
	]
	for tp in torch_positions:
		draw_rect(Rect2(tp.x - 3, tp.y - 10, 6, 20), Color(0.5, 0.3, 0.15))
		var flame_col = Color(C_TORCH.r, C_TORCH.g * flicker, C_TORCH.b * 0.5, 0.9)
		draw_circle(tp + Vector2(0, -14), 6 * flicker, flame_col)
		draw_circle(tp + Vector2(0, -14), 40 * flicker, Color(1, 0.6, 0.1, 0.05))


func _draw_enemies() -> void:
	for e in enemies:
		if not e["alive"]:
			continue
		var p = e["pos"]
		var flash = e["hit_flash"] > 0
		var anim = e["anim_timer"]

		match e["type"]:
			"slime":
				var squish = sin(anim * 3) * 3
				var body_col = Color.WHITE if flash else C_SLIME
				# Body (blobby)
				_draw_ellipse_shape(Rect2(p.x - 18, p.y - 12 + squish, 36, 24 - squish), body_col)
				# Eyes
				draw_circle(Vector2(p.x - 6, p.y - 6 + squish), 4, Color.WHITE)
				draw_circle(Vector2(p.x + 6, p.y - 6 + squish), 4, Color.WHITE)
				draw_circle(Vector2(p.x - 5, p.y - 5 + squish), 2, Color.BLACK)
				draw_circle(Vector2(p.x + 7, p.y - 5 + squish), 2, Color.BLACK)
				# HP bar
				_draw_enemy_hp(p, e)

			"bat":
				var wing = sin(anim * 10) * 12
				var body_col = Color.WHITE if flash else C_BAT
				# Wings
				draw_line(Vector2(p.x - 5, p.y), Vector2(p.x - 20, p.y - wing), body_col, 3)
				draw_line(Vector2(p.x - 20, p.y - wing), Vector2(p.x - 30, p.y + 5 - wing * 0.5), body_col, 2)
				draw_line(Vector2(p.x + 5, p.y), Vector2(p.x + 20, p.y - wing), body_col, 3)
				draw_line(Vector2(p.x + 20, p.y - wing), Vector2(p.x + 30, p.y + 5 - wing * 0.5), body_col, 2)
				# Body
				draw_circle(p, 8, body_col)
				# Eyes (red)
				draw_circle(Vector2(p.x - 3, p.y - 2), 2, Color(1, 0.2, 0.2))
				draw_circle(Vector2(p.x + 3, p.y - 2), 2, Color(1, 0.2, 0.2))
				_draw_enemy_hp(p, e)

			"skeleton":
				var body_col = Color.WHITE if flash else C_SKELETON
				# Body
				draw_rect(Rect2(p.x - 10, p.y - 12, 20, 28), body_col)
				# Head (skull)
				draw_circle(Vector2(p.x, p.y - 20), 10, body_col)
				# Eye sockets
				draw_circle(Vector2(p.x - 4, p.y - 22), 3, Color(0.1, 0.05, 0.05))
				draw_circle(Vector2(p.x + 4, p.y - 22), 3, Color(0.1, 0.05, 0.05))
				# Jaw
				draw_rect(Rect2(p.x - 5, p.y - 13, 10, 4), Color(0.1, 0.05, 0.05))
				# Arms
				draw_line(Vector2(p.x - 10, p.y - 8), Vector2(p.x - 20, p.y + 5), body_col, 2)
				draw_line(Vector2(p.x + 10, p.y - 8), Vector2(p.x + 20, p.y + 5), body_col, 2)
				# Legs
				draw_line(Vector2(p.x - 5, p.y + 16), Vector2(p.x - 8, p.y + 28), body_col, 2)
				draw_line(Vector2(p.x + 5, p.y + 16), Vector2(p.x + 8, p.y + 28), body_col, 2)
				_draw_enemy_hp(p, e)


func _draw_enemy_hp(pos: Vector2, e: Dictionary) -> void:
	if e["hp"] < e["max_hp"]:
		var bar_w = 30.0
		draw_rect(Rect2(pos.x - bar_w / 2, pos.y - 28, bar_w, 4), C_HP_BG)
		var ratio = float(e["hp"]) / e["max_hp"]
		draw_rect(Rect2(pos.x - bar_w / 2, pos.y - 28, bar_w * ratio, 4), C_HP)


func _draw_pickups() -> void:
	for p in pickups:
		var pos = p["pos"]
		var bob = sin(torch_timer * 4 + pos.x * 0.1) * 3
		if p["type"] == "coin":
			draw_circle(Vector2(pos.x, pos.y + bob), 8, C_COIN)
			draw_circle(Vector2(pos.x, pos.y + bob), 5, Color(0.9, 0.75, 0.1))
		elif p["type"] == "heart":
			draw_circle(Vector2(pos.x - 3, pos.y - 2 + bob), 5, C_HEART)
			draw_circle(Vector2(pos.x + 3, pos.y - 2 + bob), 5, C_HEART)
			var heart_pts = PackedVector2Array([
				Vector2(pos.x - 8, pos.y + bob), Vector2(pos.x, pos.y + 6 + bob), Vector2(pos.x + 8, pos.y + bob)
			])
			draw_colored_polygon(heart_pts, C_HEART)
		# Blink near expire
		if p["timer"] < 2.0 and int(p["timer"] * 6) % 2 == 0:
			return


func _draw_particles() -> void:
	for p in particles:
		var alpha = p["life"] / p["max_life"]
		var col = Color(p["color"].r, p["color"].g, p["color"].b, alpha)
		draw_circle(p["pos"], p["size"] * alpha, col)


func _draw_player() -> void:
	var cx = player_pos.x
	var cy = player_pos.y
	var bounce = sin(walk_timer) * 3 if is_walking else 0

	# Invincibility blink
	if invincible_timer > 0 and int(invincible_timer * 10) % 2 == 0:
		return

	# Shadow
	_draw_ellipse_shape(Rect2(cx - 18, cy + 15, 36, 12), Color(0, 0, 0, 0.3))

	# Body
	draw_rect(Rect2(cx - 12, cy - 15 + bounce, 24, 30), C_PLAYER_BODY)
	# Head
	draw_circle(Vector2(cx, cy - 22 + bounce), 12, C_PLAYER_HEAD)

	# Eyes
	var eye_offset = Vector2.ZERO
	match player_dir:
		0: eye_offset = Vector2(0, 2)
		1: eye_offset = Vector2(0, -3)
		2: eye_offset = Vector2(-3, 0)
		3: eye_offset = Vector2(3, 0)
	draw_circle(Vector2(cx - 4, cy - 24 + bounce) + eye_offset, 2, Color.WHITE)
	draw_circle(Vector2(cx + 4, cy - 24 + bounce) + eye_offset, 2, Color.WHITE)
	draw_circle(Vector2(cx - 3.5, cy - 24 + bounce) + eye_offset, 1, Color.BLACK)
	draw_circle(Vector2(cx + 4.5, cy - 24 + bounce) + eye_offset, 1, Color.BLACK)

	# Equipment visuals
	if "sword" in inventory_types:
		var sword_col = C_GOLD if inventory_types.count("sword") >= 2 else Color(0.7, 0.7, 0.8)
		match player_dir:
			3: draw_line(Vector2(cx + 14, cy - 5 + bounce), Vector2(cx + 28, cy - 20 + bounce), sword_col, 3)
			2: draw_line(Vector2(cx - 14, cy - 5 + bounce), Vector2(cx - 28, cy - 20 + bounce), sword_col, 3)
			_: draw_line(Vector2(cx + 14, cy - 5 + bounce), Vector2(cx + 28, cy - 20 + bounce), sword_col, 3)

	if "shield" in inventory_types:
		match player_dir:
			2: draw_circle(Vector2(cx + 16, cy - 2 + bounce), 10, Color(0.2, 0.5, 0.8, 0.8))
			3: draw_circle(Vector2(cx - 16, cy - 2 + bounce), 10, Color(0.2, 0.5, 0.8, 0.8))
			_: draw_circle(Vector2(cx - 16, cy - 2 + bounce), 10, Color(0.2, 0.5, 0.8, 0.8))

	if "helmet" in inventory_types:
		draw_rect(Rect2(cx - 13, cy - 33 + bounce, 26, 8), Color(0.5, 0.5, 0.6))

	if "boots" in inventory_types:
		var boot_col = Color(0.6, 0.2, 0.2)
		draw_rect(Rect2(cx - 9, cy + 14 + bounce, 8, 6), boot_col)
		draw_rect(Rect2(cx + 1, cy + 14 + bounce, 8, 6), boot_col)

	# Feet animation
	if is_walking:
		var foot_off = sin(walk_timer) * 5
		draw_rect(Rect2(cx - 8, cy + 15 + bounce, 7, 5), Color(0.5, 0.35, 0.2))
		draw_rect(Rect2(cx + 1 + foot_off, cy + 15 + bounce, 7, 5), Color(0.5, 0.35, 0.2))
	else:
		draw_rect(Rect2(cx - 8, cy + 15, 7, 5), Color(0.5, 0.35, 0.2))
		draw_rect(Rect2(cx + 1, cy + 15, 7, 5), Color(0.5, 0.35, 0.2))

	# Attack swing arc
	if attack_timer > 0:
		var swing_angle_start = 0.0
		var swing_angle_end = 0.0
		var swing_center = player_pos
		match player_dir:
			0: swing_angle_start = 0.2; swing_angle_end = PI - 0.2; swing_center.y += 20
			1: swing_angle_start = PI + 0.2; swing_angle_end = TAU - 0.2; swing_center.y -= 20
			2: swing_angle_start = PI / 2 + 0.2; swing_angle_end = PI * 1.5 - 0.2; swing_center.x -= 20
			3: swing_angle_start = -PI / 2 + 0.2; swing_angle_end = PI / 2 - 0.2; swing_center.x += 20

		var progress_val = 1.0 - (attack_timer / ATTACK_DURATION)
		var alpha = 0.6 * (1.0 - progress_val)
		for i in range(8):
			var t = float(i) / 7.0
			var angle = lerp(swing_angle_start, swing_angle_end, t)
			var r = ATTACK_RANGE * (0.5 + progress_val * 0.5)
			var pt = swing_center + Vector2(cos(angle), sin(angle)) * r
			draw_circle(pt, 4 - progress_val * 3, Color(1, 1, 1, alpha))


func _draw_hud() -> void:
	var font = ThemeDB.fallback_font

	# HUD bar background
	draw_rect(Rect2(0, 0, 1280, 45), Color(0, 0, 0, 0.6))

	# HP bar
	draw_rect(Rect2(20, 10, 160, 24), C_HP_BG)
	var hp_w = 156.0 * (float(hp) / max_hp)
	draw_rect(Rect2(22, 12, hp_w, 20), C_HP)
	draw_string(font, Vector2(55, 28), "HP " + str(hp) + "/" + str(max_hp), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_TEXT)

	# Score
	draw_string(font, Vector2(200, 30), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_GOLD)

	# Stats
	var stats = "ATK:" + str(atk) + "  DEF:" + str(defense)
	draw_string(font, Vector2(350, 30), stats, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.7, 0.8, 1.0))

	# Title
	var title = config.get("title", "Quiz Dungeon")
	draw_string(font, Vector2(900, 30), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_REWARD)

	# Inventory at bottom
	if inventory.size() > 0:
		draw_rect(Rect2(0, 695, 1280, 25), Color(0, 0, 0, 0.5))
		var inv_text = "Equipment: " + ", ".join(inventory)
		draw_string(font, Vector2(20, 714), inv_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, C_REWARD)

	# Controls hint
	draw_string(font, Vector2(550, 30), "WASD: Move  SPACE: Attack/Interact", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.5, 0.5, 0.6))


func _draw_question() -> void:
	if current_room >= rooms.size():
		return
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.5))

	var panel_x = 200.0
	var panel_y = 140.0
	var panel_w = 880.0
	var panel_h = 440.0
	draw_rect(Rect2(panel_x, panel_y, panel_w, panel_h), C_QUESTION_BG)
	draw_rect(Rect2(panel_x, panel_y, panel_w, 4), C_GOLD)

	var font = ThemeDB.fallback_font
	var room = rooms[current_room]

	var reward_text = "Reward: " + room.get("reward_name", "???")
	draw_string(font, Vector2(panel_x + 20, panel_y + 30), reward_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_REWARD)

	var q_text = room.get("question", "")
	var q_w = font.get_string_size(q_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - q_w / 2, panel_y + 80), q_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)

	for i in range(shuffled_answers.size()):
		var ax = panel_x + 40
		var ay = panel_y + 120 + i * 70
		var aw = panel_w - 80
		var ah = 55
		draw_rect(Rect2(ax, ay, aw, ah), C_ANSWER_BG)
		draw_rect(Rect2(ax, ay, 45, ah), Color(0.35, 0.3, 0.55))
		draw_string(font, Vector2(ax + 15, ay + 34), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_GOLD)
		draw_string(font, Vector2(ax + 60, ay + 34), shuffled_answers[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_TEXT)

	draw_string(font, Vector2(panel_x + 20, panel_y + panel_h - 20),
		"Press 1-4 to answer", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(0.6, 0.55, 0.7))


func _draw_result() -> void:
	var font = ThemeDB.fallback_font
	var text: String
	var col: Color
	if result_correct:
		var room = rooms[current_room]
		text = "CORRECT! Got " + room.get("reward_name", "reward") + "!"
		col = C_CORRECT
	else:
		text = "WRONG! Lost 1 HP"
		col = C_WRONG
	draw_rect(Rect2(300, 330, 680, 60), Color(0, 0, 0, 0.8))
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 28).x
	draw_string(font, Vector2(640 - tw / 2, 368), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, col)


func _draw_game_over() -> void:
	_draw_room()
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.75))
	var font = ThemeDB.fallback_font
	var t1 = "DUNGEON DEFEAT"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 280), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_WRONG)
	var t2 = "Rooms cleared: " + str(current_room) + "/" + str(rooms.size())
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 340), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	var t2b = "Enemies defeated: " + str(score)
	var tw2b = font.get_string_size(t2b, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw2b / 2, 380), t2b, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)
	var t3 = "Press SPACE to retry"
	var tw3 = font.get_string_size(t3, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw3 / 2, 430), t3, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _draw_victory() -> void:
	_draw_room()
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.6))
	var font = ThemeDB.fallback_font
	var t1 = "DUNGEON CLEARED!"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 230), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_CORRECT)

	var total_q = rooms.size()
	var correct_q = 0
	for r in rooms:
		if r.get("reward_name", "") in inventory:
			correct_q += 1
	var pct = round(float(correct_q) / total_q * 100) if total_q > 0 else 0
	var t2 = "Questions: " + str(correct_q) + "/" + str(total_q) + " (" + str(pct) + "%)"
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 300), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)

	var t2b = "Enemies defeated: " + str(score)
	var tw2b = font.get_string_size(t2b, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw2b / 2, 340), t2b, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)

	var num_stars = 3 if pct >= 90 else 2 if pct >= 70 else 1 if pct >= 40 else 0
	var star_text = ""
	for i in range(num_stars):
		star_text += "★ "
	for i in range(3 - num_stars):
		star_text += "☆ "
	var tw3 = font.get_string_size(star_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 40).x
	draw_string(font, Vector2(640 - tw3 / 2, 400), star_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 40, C_GOLD)

	if inventory.size() > 0:
		var inv = "Collected: " + ", ".join(inventory)
		var tw4 = font.get_string_size(inv, HORIZONTAL_ALIGNMENT_CENTER, -1, 16).x
		draw_string(font, Vector2(640 - tw4 / 2, 440), inv, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_REWARD)

	var t5 = "Press SPACE to play again"
	var tw5 = font.get_string_size(t5, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw5 / 2, 490), t5, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _draw_ellipse_shape(rect: Rect2, color: Color) -> void:
	var center = rect.get_center()
	var pts = PackedVector2Array()
	for i in range(16):
		var angle = i * TAU / 16
		pts.append(Vector2(center.x + cos(angle) * rect.size.x / 2, center.y + sin(angle) * rect.size.y / 2))
	draw_colored_polygon(pts, color)
