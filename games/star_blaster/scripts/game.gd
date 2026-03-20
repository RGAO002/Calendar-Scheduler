extends Node2D
## Star Blaster — Space shooter with enemy ships, power-ups, and combos.
##
## Ship moves left/right. Shoot correct-answer asteroids while dodging
## enemy fire. Combos multiply your score. Collect power-ups!

# ── Config ──
var config: Dictionary = {}
var questions: Array = []
var current_q: int = 0
var score: int = 0
var lives: int = 3
var game_active: bool = false

# ── Ship ──
var ship_x: float = 640.0
var ship_y: float = 640.0
const SHIP_SPEED: float = 400.0
const SHIP_W: float = 60.0
const SHIP_H: float = 40.0
var ship_shield: bool = false
var shield_timer: float = 0.0
var rapid_fire: bool = false
var rapid_timer: float = 0.0

# ── Bullets ──
var bullets: Array = []
const BULLET_SPEED: float = 650.0
const BULLET_W: float = 4.0
const BULLET_H: float = 16.0
var shoot_cooldown: float = 0.0

# ── Asteroids (answer choices) ──
var asteroids: Array = []
const ASTEROID_SPEED: float = 60.0
const ASTEROID_SIZE: float = 70.0

# ── Enemy ships ──
var enemy_ships: Array = []
# {pos, hp, type, timer, shoot_cd, dir, alive, anim}
# types: "scout" (fast, 1hp), "fighter" (2hp, shoots), "bomber" (3hp, slow, big shots)

# ── Enemy bullets ──
var enemy_bullets: Array = []

# ── Power-ups ──
var powerups: Array = []
# {pos, type, speed}  types: "shield", "rapid", "life", "double"

# ── Stars background ──
var stars: Array = []

# ── Explosions / Particles ──
var explosions: Array = []
var particles: Array = []

# ── Engine trail ──
var trail: Array = []

# ── Combo system ──
var combo: int = 0
var combo_timer: float = 0.0
const COMBO_DECAY: float = 5.0

# ── UI state ──
var show_result: bool = false
var result_timer: float = 0.0
var result_correct: bool = false
var game_over: bool = false
var victory: bool = false
var score_popup: Array = []  # {pos, text, timer, color}

# ── Colors ──
const C_BG = Color(0.04, 0.03, 0.12)
const C_SHIP = Color(0.2, 0.8, 1.0)
const C_SHIP_WING = Color(0.15, 0.6, 0.85)
const C_BULLET = Color(1.0, 1.0, 0.3)
const C_ASTEROID = Color(0.55, 0.45, 0.35)
const C_CORRECT = Color(0.2, 0.9, 0.3)
const C_WRONG = Color(0.9, 0.25, 0.2)
const C_TEXT = Color(1, 1, 1)
const C_QUESTION = Color(1.0, 0.95, 0.6)
const C_HUD = Color(0.7, 0.8, 1.0)
const C_EXPLOSION = Color(1.0, 0.6, 0.1)
const C_ENEMY = Color(0.9, 0.3, 0.2)
const C_ENEMY_BULLET = Color(1.0, 0.3, 0.3)
const C_SHIELD = Color(0.3, 0.7, 1.0, 0.4)
const C_COMBO = Color(1.0, 0.5, 0.0)


func _ready() -> void:
	_load_config()
	_init_stars()
	_start_game()


func _load_config() -> void:
	if OS.has_feature("web"):
		var js_config = JavaScriptBridge.eval("JSON.stringify(window.gameConfig || {})")
		if js_config and js_config != "{}":
			var json = JSON.new()
			json.parse(js_config)
			config = json.data
			questions = config.get("questions", [])
			return
	var file = FileAccess.open("res://config.json", FileAccess.READ)
	if file:
		var json = JSON.new()
		json.parse(file.get_as_text())
		config = json.data
		questions = config.get("questions", [])
		file.close()


func _init_stars() -> void:
	stars.clear()
	for i in range(100):
		stars.append({
			"x": randf_range(0, 1280),
			"y": randf_range(0, 720),
			"size": randf_range(0.5, 2.5),
			"speed": randf_range(15, 60),
			"brightness": randf_range(0.2, 1.0),
			"twinkle": randf_range(0, TAU),
		})


func _start_game() -> void:
	score = 0
	lives = 3
	current_q = 0
	combo = 0
	combo_timer = 0
	game_active = true
	game_over = false
	victory = false
	ship_x = 640.0
	ship_y = 640.0
	ship_shield = false
	rapid_fire = false
	bullets.clear()
	explosions.clear()
	particles.clear()
	enemy_ships.clear()
	enemy_bullets.clear()
	powerups.clear()
	trail.clear()
	score_popup.clear()
	_spawn_question()


func _spawn_question() -> void:
	asteroids.clear()
	if current_q >= questions.size():
		victory = true
		game_active = false
		return

	var q = questions[current_q]
	var answers: Array = [q["correct"]]
	for w in q.get("wrong", []):
		answers.append(w)

	# Shuffle
	for i in range(answers.size() - 1, 0, -1):
		var j = randi() % (i + 1)
		var tmp = answers[i]
		answers[i] = answers[j]
		answers[j] = tmp

	var count = answers.size()
	var spacing = 1280.0 / (count + 1)
	for i in range(count):
		asteroids.append({
			"x": spacing * (i + 1),
			"y": -ASTEROID_SIZE,
			"w": ASTEROID_SIZE * 1.5,
			"h": ASTEROID_SIZE,
			"text": answers[i],
			"correct": answers[i] == q["correct"],
			"alive": true,
			"rotation": randf_range(0, TAU),
			"rot_speed": randf_range(-1.5, 1.5),
		})

	# Spawn enemy ships with each question (escalating difficulty)
	var num_enemies = mini(1 + current_q / 2, 4)
	for i in range(num_enemies):
		var etype: String
		if current_q < 3:
			etype = "scout"
		elif current_q < 6:
			etype = ["scout", "fighter"][randi() % 2]
		else:
			etype = ["scout", "fighter", "bomber"][randi() % 3]

		var ex = randf_range(100, 1180)
		var ey = randf_range(-200, -50)

		var ehp = 1
		var espeed = 0.0
		match etype:
			"scout":
				ehp = 1
				espeed = 100.0
			"fighter":
				ehp = 2
				espeed = 60.0
			"bomber":
				ehp = 3
				espeed = 35.0

		enemy_ships.append({
			"pos": Vector2(ex, ey),
			"hp": ehp,
			"type": etype,
			"timer": 0.0,
			"shoot_cd": randf_range(1.5, 3.0),
			"dir": Vector2(randf_range(-0.5, 0.5), 1).normalized(),
			"alive": true,
			"anim": randf_range(0, TAU),
			"speed": espeed,
			"target_y": randf_range(100, 350),
		})


func _process(delta: float) -> void:
	if game_over or victory:
		if Input.is_action_just_pressed("shoot"):
			_start_game()
		# Still update stars for visual
		_update_stars(delta)
		queue_redraw()
		return

	if show_result:
		result_timer -= delta
		if result_timer <= 0:
			show_result = false
			current_q += 1
			_spawn_question()
		_update_stars(delta)
		_update_particles(delta)
		_update_explosions(delta)
		queue_redraw()
		return

	if not game_active:
		queue_redraw()
		return

	# Combo decay
	if combo > 0:
		combo_timer -= delta
		if combo_timer <= 0:
			combo = 0

	# Power-up timers
	if shield_timer > 0:
		shield_timer -= delta
		if shield_timer <= 0:
			ship_shield = false
	if rapid_timer > 0:
		rapid_timer -= delta
		if rapid_timer <= 0:
			rapid_fire = false

	# Shoot cooldown
	if shoot_cooldown > 0:
		shoot_cooldown -= delta

	# Ship movement
	if Input.is_action_pressed("move_left"):
		ship_x -= SHIP_SPEED * delta
	if Input.is_action_pressed("move_right"):
		ship_x += SHIP_SPEED * delta
	# Vertical dodge
	if Input.is_action_pressed("move_up"):
		ship_y -= SHIP_SPEED * 0.6 * delta
	if Input.is_action_pressed("move_down"):
		ship_y += SHIP_SPEED * 0.6 * delta
	ship_x = clampf(ship_x, SHIP_W, 1280 - SHIP_W)
	ship_y = clampf(ship_y, 400, 700)

	# Engine trail
	trail.append({"pos": Vector2(ship_x, ship_y + 10), "life": 0.3})

	# Shoot
	var cd = 0.12 if rapid_fire else 0.25
	if Input.is_action_pressed("shoot") and shoot_cooldown <= 0:
		bullets.append({"x": ship_x, "y": ship_y - SHIP_H / 2})
		if rapid_fire:
			bullets.append({"x": ship_x - 12, "y": ship_y - SHIP_H / 2 + 8})
			bullets.append({"x": ship_x + 12, "y": ship_y - SHIP_H / 2 + 8})
		shoot_cooldown = cd

	# Update bullets
	var new_bullets: Array = []
	for b in bullets:
		b["y"] -= BULLET_SPEED * delta
		if b["y"] > -10:
			new_bullets.append(b)
	bullets = new_bullets

	# Update asteroids
	for a in asteroids:
		if a["alive"]:
			a["y"] += ASTEROID_SPEED * delta
			a["rotation"] += a["rot_speed"] * delta
			if a["y"] > 720:
				if a["correct"]:
					lives -= 1
					combo = 0
					_add_explosion(a["x"], 700)
					if lives <= 0:
						game_over = true
						game_active = false
					else:
						show_result = true
						result_correct = false
						result_timer = 1.5
				a["alive"] = false

	# Bullet-asteroid collisions
	for b in bullets:
		for a in asteroids:
			if not a["alive"]:
				continue
			if abs(b["x"] - a["x"]) < a["w"] / 2 and abs(b["y"] - a["y"]) < a["h"] / 2:
				a["alive"] = false
				_add_explosion(a["x"], a["y"])
				if a["correct"]:
					combo += 1
					combo_timer = COMBO_DECAY
					var pts = 10 * maxi(combo, 1)
					score += pts
					result_correct = true
					score_popup.append({"pos": Vector2(a["x"], a["y"]), "text": "+" + str(pts), "timer": 1.0, "color": C_CORRECT})
					if combo > 1:
						score_popup.append({"pos": Vector2(a["x"], a["y"] + 20), "text": str(combo) + "x COMBO!", "timer": 1.2, "color": C_COMBO})
				else:
					combo = 0
					lives -= 1
					result_correct = false
					if lives <= 0:
						game_over = true
						game_active = false
						return
				show_result = true
				result_timer = 1.2
				for a2 in asteroids:
					a2["alive"] = false
				b["y"] = -100
				break

	# Bullet-enemy collisions
	for b in bullets:
		for e in enemy_ships:
			if not e["alive"]:
				continue
			if abs(b["x"] - e["pos"].x) < 25 and abs(b["y"] - e["pos"].y) < 20:
				e["hp"] -= 1
				b["y"] = -100
				for i in range(4):
					_spawn_particle(e["pos"], C_EXPLOSION)
				if e["hp"] <= 0:
					e["alive"] = false
					_add_explosion(e["pos"].x, e["pos"].y)
					score += 5
					score_popup.append({"pos": e["pos"], "text": "+5", "timer": 0.8, "color": C_HUD})
					# Maybe drop power-up
					if randf() < 0.35:
						var ptypes = ["shield", "rapid", "life", "double"]
						powerups.append({
							"pos": Vector2(e["pos"]),
							"type": ptypes[randi() % ptypes.size()],
							"speed": 80.0,
						})
				break

	# Update enemy ships
	_update_enemy_ships(delta)

	# Update enemy bullets & check collision with player
	_update_enemy_bullets(delta)

	# Update power-ups
	_update_powerups(delta)

	# Update stars, explosions, particles
	_update_stars(delta)
	_update_explosions(delta)
	_update_particles(delta)
	_update_trail(delta)
	_update_score_popups(delta)

	queue_redraw()


func _update_enemy_ships(delta: float) -> void:
	for e in enemy_ships:
		if not e["alive"]:
			continue
		e["anim"] += delta
		e["timer"] += delta

		# Movement
		if e["pos"].y < e["target_y"]:
			e["pos"].y += e["speed"] * delta
		else:
			# Strafe left-right
			e["pos"].x += sin(e["anim"] * 1.5) * e["speed"] * 0.7 * delta

		e["pos"].x = clampf(e["pos"].x, 40, 1240)

		# Shooting
		if e["pos"].y > 50:
			e["shoot_cd"] -= delta
			if e["shoot_cd"] <= 0:
				match e["type"]:
					"fighter":
						enemy_bullets.append({"pos": Vector2(e["pos"].x, e["pos"].y + 15), "vel": Vector2(0, 250)})
						e["shoot_cd"] = 2.0
					"bomber":
						# Aimed shot toward player
						var dir = (Vector2(ship_x, ship_y) - e["pos"]).normalized()
						enemy_bullets.append({"pos": Vector2(e["pos"]), "vel": dir * 200})
						e["shoot_cd"] = 3.0
					"scout":
						e["shoot_cd"] = 99  # scouts don't shoot

		# Remove if off screen
		if e["pos"].y > 750:
			e["alive"] = false


func _update_enemy_bullets(delta: float) -> void:
	var new_eb: Array = []
	for eb in enemy_bullets:
		eb["pos"] += eb["vel"] * delta
		if eb["pos"].y > 730 or eb["pos"].y < -10 or eb["pos"].x < -10 or eb["pos"].x > 1290:
			continue
		# Check hit player
		if abs(eb["pos"].x - ship_x) < 20 and abs(eb["pos"].y - ship_y) < 20:
			if ship_shield:
				ship_shield = false
				shield_timer = 0
				for i in range(8):
					_spawn_particle(Vector2(ship_x, ship_y), C_SHIELD)
				continue
			else:
				lives -= 1
				_add_explosion(ship_x, ship_y)
				for i in range(8):
					_spawn_particle(Vector2(ship_x, ship_y), C_WRONG)
				if lives <= 0:
					game_over = true
					game_active = false
					return
				continue
		new_eb.append(eb)
	enemy_bullets = new_eb


func _update_powerups(delta: float) -> void:
	var new_pu: Array = []
	for pu in powerups:
		pu["pos"].y += pu["speed"] * delta
		if pu["pos"].y > 740:
			continue
		# Collect
		if abs(pu["pos"].x - ship_x) < 30 and abs(pu["pos"].y - ship_y) < 25:
			match pu["type"]:
				"shield":
					ship_shield = true
					shield_timer = 10.0
					score_popup.append({"pos": pu["pos"], "text": "SHIELD!", "timer": 1.0, "color": C_SHIELD})
				"rapid":
					rapid_fire = true
					rapid_timer = 8.0
					score_popup.append({"pos": pu["pos"], "text": "RAPID FIRE!", "timer": 1.0, "color": C_BULLET})
				"life":
					lives = mini(lives + 1, 5)
					score_popup.append({"pos": pu["pos"], "text": "+1 LIFE!", "timer": 1.0, "color": C_CORRECT})
				"double":
					score += 20
					score_popup.append({"pos": pu["pos"], "text": "+20 BONUS!", "timer": 1.0, "color": C_COMBO})
			for i in range(8):
				_spawn_particle(pu["pos"], C_CORRECT)
			continue
		new_pu.append(pu)
	powerups = new_pu


func _update_stars(delta: float) -> void:
	for s in stars:
		s["y"] += s["speed"] * delta
		s["twinkle"] += delta * 2
		if s["y"] > 720:
			s["y"] = 0
			s["x"] = randf_range(0, 1280)


func _update_trail(delta: float) -> void:
	var new_trail: Array = []
	for t in trail:
		t["life"] -= delta
		if t["life"] > 0:
			new_trail.append(t)
	trail = new_trail


func _update_score_popups(delta: float) -> void:
	var new_sp: Array = []
	for sp in score_popup:
		sp["timer"] -= delta
		sp["pos"].y -= 40 * delta
		if sp["timer"] > 0:
			new_sp.append(sp)
	score_popup = new_sp


func _add_explosion(x: float, y: float) -> void:
	explosions.append({"x": x, "y": y, "timer": 0.5, "radius": 10.0})
	for i in range(12):
		_spawn_particle(Vector2(x, y), C_EXPLOSION)


func _spawn_particle(pos: Vector2, col: Color) -> void:
	particles.append({
		"pos": Vector2(pos),
		"vel": Vector2(randf_range(-120, 120), randf_range(-120, 120)),
		"color": col,
		"life": randf_range(0.3, 0.7),
		"max_life": 0.7,
		"size": randf_range(1.5, 3.5),
	})


func _update_explosions(delta: float) -> void:
	var new_ex: Array = []
	for e in explosions:
		e["timer"] -= delta
		e["radius"] += 150 * delta
		if e["timer"] > 0:
			new_ex.append(e)
	explosions = new_ex


func _update_particles(delta: float) -> void:
	var new_p: Array = []
	for p in particles:
		p["life"] -= delta
		if p["life"] > 0:
			p["pos"] += p["vel"] * delta
			p["vel"].y += 60 * delta
			new_p.append(p)
	particles = new_p


# ══════════════════════════════════════════════════
# DRAWING
# ══════════════════════════════════════════════════

func _draw() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), C_BG)

	# Nebula background glow
	draw_circle(Vector2(300, 200), 200, Color(0.1, 0.05, 0.2, 0.15))
	draw_circle(Vector2(900, 400), 180, Color(0.05, 0.1, 0.2, 0.1))

	# Stars
	for s in stars:
		var twinkle = (sin(s["twinkle"]) * 0.3 + 0.7) * s["brightness"]
		draw_circle(Vector2(s["x"], s["y"]), s["size"], Color(1, 1, 1, twinkle * 0.7))

	if game_over:
		_draw_game_over()
		return
	if victory:
		_draw_victory()
		return

	# Engine trail
	for t in trail:
		var alpha = t["life"] / 0.3
		draw_circle(t["pos"], 3 * alpha, Color(1, 0.5, 0.1, alpha * 0.4))

	# Question bar
	_draw_question_bar()

	# Power-ups
	for pu in powerups:
		_draw_powerup(pu)

	# Asteroids
	for a in asteroids:
		if a["alive"]:
			_draw_asteroid(a)

	# Enemy ships
	for e in enemy_ships:
		if e["alive"]:
			_draw_enemy_ship(e)

	# Enemy bullets
	for eb in enemy_bullets:
		draw_circle(eb["pos"], 4, C_ENEMY_BULLET)
		draw_circle(eb["pos"], 2, Color(1, 0.6, 0.5))

	# Ship
	_draw_ship()

	# Bullets
	for b in bullets:
		draw_rect(Rect2(b["x"] - BULLET_W / 2, b["y"] - BULLET_H / 2, BULLET_W, BULLET_H), C_BULLET)
		draw_rect(Rect2(b["x"] - BULLET_W, b["y"] - BULLET_H / 2, BULLET_W * 2, BULLET_H), Color(1, 1, 0.3, 0.3))

	# Explosions
	for e in explosions:
		var alpha = e["timer"] / 0.5
		draw_circle(Vector2(e["x"], e["y"]), e["radius"], Color(1.0, 0.6, 0.1, alpha * 0.6))
		draw_circle(Vector2(e["x"], e["y"]), e["radius"] * 0.5, Color(1.0, 0.9, 0.3, alpha * 0.4))

	# Particles
	for p in particles:
		var alpha = p["life"] / p["max_life"]
		draw_circle(p["pos"], p["size"] * alpha, Color(p["color"].r, p["color"].g, p["color"].b, alpha))

	# Score popups
	var font = ThemeDB.fallback_font
	for sp in score_popup:
		var alpha = sp["timer"] / 1.0
		var col = Color(sp["color"].r, sp["color"].g, sp["color"].b, alpha)
		draw_string(font, sp["pos"], sp["text"], HORIZONTAL_ALIGNMENT_LEFT, -1, 20, col)

	# HUD
	_draw_hud()

	# Result flash
	if show_result:
		_draw_result_flash()


func _draw_ship() -> void:
	var sx = ship_x
	var sy = ship_y
	# Body
	var body = PackedVector2Array([
		Vector2(sx, sy - SHIP_H),
		Vector2(sx - SHIP_W / 2, sy),
		Vector2(sx + SHIP_W / 2, sy),
	])
	draw_colored_polygon(body, C_SHIP)
	# Wings
	var lwing = PackedVector2Array([
		Vector2(sx - SHIP_W / 2, sy),
		Vector2(sx - SHIP_W, sy + 10),
		Vector2(sx - SHIP_W / 4, sy - 5),
	])
	var rwing = PackedVector2Array([
		Vector2(sx + SHIP_W / 2, sy),
		Vector2(sx + SHIP_W, sy + 10),
		Vector2(sx + SHIP_W / 4, sy - 5),
	])
	draw_colored_polygon(lwing, C_SHIP_WING)
	draw_colored_polygon(rwing, C_SHIP_WING)
	# Engine
	var flame_size = 6 + sin(score * 0.5) * 2
	draw_circle(Vector2(sx, sy + 5), flame_size, Color(1, 0.5, 0.1, 0.8))
	draw_circle(Vector2(sx, sy + 9), flame_size * 0.6, Color(1, 0.8, 0.2, 0.6))
	# Cockpit
	draw_circle(Vector2(sx, sy - 15), 5, Color(0.4, 0.9, 1.0, 0.7))

	# Shield bubble
	if ship_shield:
		var sh_alpha = 0.3 + sin(shield_timer * 4) * 0.1
		draw_circle(Vector2(sx, sy - 10), 40, Color(0.3, 0.7, 1.0, sh_alpha))

	# Rapid fire glow
	if rapid_fire:
		draw_circle(Vector2(sx - 12, sy - 5), 3, Color(1, 1, 0, 0.6))
		draw_circle(Vector2(sx + 12, sy - 5), 3, Color(1, 1, 0, 0.6))


func _draw_asteroid(a: Dictionary) -> void:
	var cx = a["x"]
	var cy = a["y"]
	var hw = a["w"] / 2
	var hh = a["h"] / 2

	var pts = PackedVector2Array()
	for i in range(8):
		var angle = i * PI / 4 + a["rotation"]
		var r_val = hw * (0.85 + 0.15 * sin(float(i) * 1.5 + a["x"] * 0.01))
		pts.append(Vector2(cx + cos(angle) * r_val, cy + sin(angle) * r_val * (hh / hw)))

	var col = C_CORRECT if a["correct"] and show_result else C_ASTEROID
	draw_colored_polygon(pts, col)
	for i in range(pts.size()):
		draw_line(pts[i], pts[(i + 1) % pts.size()], Color(0.3, 0.25, 0.2), 2.0)

	var font = ThemeDB.fallback_font
	var text = str(a["text"])
	var fsize = 14 if text.length() > 15 else 16
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, fsize).x
	draw_string(font, Vector2(cx - tw / 2, cy + fsize / 3), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize, C_TEXT)


func _draw_enemy_ship(e: Dictionary) -> void:
	var p = e["pos"]
	var bob = sin(e["anim"] * 3) * 3

	match e["type"]:
		"scout":
			# Small triangle (inverted)
			var pts = PackedVector2Array([
				Vector2(p.x, p.y + 15 + bob),
				Vector2(p.x - 15, p.y - 10 + bob),
				Vector2(p.x + 15, p.y - 10 + bob),
			])
			draw_colored_polygon(pts, Color(0.9, 0.4, 0.3))
			draw_circle(Vector2(p.x, p.y + bob), 4, Color(1, 0.8, 0.2))

		"fighter":
			# Wider ship
			var pts = PackedVector2Array([
				Vector2(p.x, p.y + 20 + bob),
				Vector2(p.x - 22, p.y - 12 + bob),
				Vector2(p.x - 8, p.y - 5 + bob),
				Vector2(p.x + 8, p.y - 5 + bob),
				Vector2(p.x + 22, p.y - 12 + bob),
			])
			draw_colored_polygon(pts, Color(0.8, 0.2, 0.2))
			draw_circle(Vector2(p.x, p.y + 5 + bob), 5, Color(1, 0.5, 0.1))
			# Gun ports
			draw_circle(Vector2(p.x - 10, p.y + 10 + bob), 2, C_ENEMY_BULLET)
			draw_circle(Vector2(p.x + 10, p.y + 10 + bob), 2, C_ENEMY_BULLET)

		"bomber":
			# Big hexagonal
			draw_rect(Rect2(p.x - 20, p.y - 15 + bob, 40, 30), Color(0.6, 0.15, 0.15))
			draw_rect(Rect2(p.x - 15, p.y - 10 + bob, 30, 20), Color(0.7, 0.2, 0.2))
			draw_circle(Vector2(p.x, p.y + 15 + bob), 6, Color(1, 0.3, 0.1))

	# HP indicator
	if e["hp"] > 1:
		for i in range(e["hp"]):
			draw_circle(Vector2(p.x - 8 + i * 8, p.y - 20 + bob), 2, Color(1, 0.3, 0.3))


func _draw_powerup(pu: Dictionary) -> void:
	var p = pu["pos"]
	var bob = sin(p.y * 0.05) * 4

	# Glowing background
	draw_circle(Vector2(p.x, p.y + bob), 16, Color(1, 1, 1, 0.1))

	match pu["type"]:
		"shield":
			draw_circle(Vector2(p.x, p.y + bob), 12, Color(0.2, 0.5, 0.9, 0.7))
			draw_circle(Vector2(p.x, p.y + bob), 8, Color(0.4, 0.7, 1.0, 0.5))
		"rapid":
			draw_rect(Rect2(p.x - 2, p.y - 10 + bob, 4, 20), C_BULLET)
			draw_rect(Rect2(p.x - 8, p.y - 6 + bob, 4, 12), Color(1, 0.8, 0.2, 0.7))
			draw_rect(Rect2(p.x + 4, p.y - 6 + bob, 4, 12), Color(1, 0.8, 0.2, 0.7))
		"life":
			draw_circle(Vector2(p.x - 4, p.y - 3 + bob), 6, Color(1, 0.3, 0.4))
			draw_circle(Vector2(p.x + 4, p.y - 3 + bob), 6, Color(1, 0.3, 0.4))
			var heart = PackedVector2Array([
				Vector2(p.x - 10, p.y + bob), Vector2(p.x, p.y + 8 + bob), Vector2(p.x + 10, p.y + bob)
			])
			draw_colored_polygon(heart, Color(1, 0.3, 0.4))
		"double":
			var font = ThemeDB.fallback_font
			draw_circle(Vector2(p.x, p.y + bob), 12, Color(1, 0.8, 0, 0.5))
			draw_string(font, Vector2(p.x - 6, p.y + 6 + bob), "x2", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_COMBO)


func _draw_question_bar() -> void:
	if current_q >= questions.size():
		return
	draw_rect(Rect2(0, 0, 1280, 55), Color(0, 0, 0, 0.7))
	var q = questions[current_q]
	var font = ThemeDB.fallback_font
	var text = q.get("question", "")
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw / 2, 35), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_QUESTION)


func _draw_hud() -> void:
	var font = ThemeDB.fallback_font
	# Score
	draw_string(font, Vector2(20, 690), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_HUD)
	# Lives as hearts
	for i in range(lives):
		var hx = 1220.0 - i * 30
		draw_circle(Vector2(hx - 4, 682), 7, Color(1, 0.2, 0.3))
		draw_circle(Vector2(hx + 4, 682), 7, Color(1, 0.2, 0.3))
		var heart_pts = PackedVector2Array([
			Vector2(hx - 11, 685), Vector2(hx, 695), Vector2(hx + 11, 685)
		])
		draw_colored_polygon(heart_pts, Color(1, 0.2, 0.3))
	# Question counter
	var qtext = "Q: " + str(current_q + 1) + "/" + str(questions.size())
	draw_string(font, Vector2(570, 690), qtext, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_HUD)
	# Combo
	if combo > 1:
		var combo_text = str(combo) + "x COMBO"
		var combo_col = Color(C_COMBO.r, C_COMBO.g, C_COMBO.b, 0.6 + sin(combo_timer * 5) * 0.4)
		draw_string(font, Vector2(750, 690), combo_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, combo_col)
	# Active power-ups
	var pu_y = 660.0
	if ship_shield:
		draw_string(font, Vector2(20, pu_y), "SHIELD " + str(int(shield_timer)) + "s", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_SHIELD)
		pu_y -= 18
	if rapid_fire:
		draw_string(font, Vector2(20, pu_y), "RAPID " + str(int(rapid_timer)) + "s", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, C_BULLET)


func _draw_result_flash() -> void:
	var font = ThemeDB.fallback_font
	var text = "CORRECT!" if result_correct else "MISS!"
	var col = C_CORRECT if result_correct else C_WRONG
	draw_rect(Rect2(0, 320, 1280, 60), Color(0, 0, 0, 0.5))
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 36).x
	draw_string(font, Vector2(640 - tw / 2, 358), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 36, col)


func _draw_game_over() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.7))
	var font = ThemeDB.fallback_font
	var t1 = "GAME OVER"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 280), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_WRONG)
	var t2 = "Score: " + str(score)
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 28).x
	draw_string(font, Vector2(640 - tw2 / 2, 340), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, C_TEXT)
	var t3 = "Questions: " + str(current_q) + "/" + str(questions.size())
	var tw3 = font.get_string_size(t3, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw3 / 2, 380), t3, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_HUD)
	var t4 = "Press SPACE to restart"
	var tw4 = font.get_string_size(t4, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw4 / 2, 440), t4, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_HUD)


func _draw_victory() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.6))
	var font = ThemeDB.fallback_font
	var t1 = "MISSION COMPLETE!"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 250), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_CORRECT)
	var t2 = "Score: " + str(score)
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 32).x
	draw_string(font, Vector2(640 - tw2 / 2, 320), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 32, C_TEXT)
	var pct = round(float(score) / (questions.size() * 10) * 100)
	pct = mini(pct, 100)
	var num_stars = 3 if pct >= 90 else 2 if pct >= 60 else 1 if pct >= 30 else 0
	var star_text = ""
	for i in range(num_stars):
		star_text += "★ "
	for i in range(3 - num_stars):
		star_text += "☆ "
	var tw3 = font.get_string_size(star_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 40).x
	draw_string(font, Vector2(640 - tw3 / 2, 390), star_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 40, Color(1, 0.85, 0))
	var t5 = "Best Combo: " + str(combo) + "x"
	var tw5 = font.get_string_size(t5, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw5 / 2, 430), t5, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_COMBO)
	var t4 = "Press SPACE to play again"
	var tw4 = font.get_string_size(t4, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw4 / 2, 480), t4, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_HUD)
