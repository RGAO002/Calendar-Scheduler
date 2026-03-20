extends Node2D
## Knowledge Runner — Endless runner where the character runs forward
## and must jump into the lane with the correct answer.
##
## 3 lanes, character auto-runs. Question appears, 3 answer gates approach.
## Jump into the correct gate to score. Wrong gate = lose a life.

# ── Config ──
var config: Dictionary = {}
var questions: Array = []
var current_q: int = 0
var score: int = 0
var lives: int = 3
var game_active: bool = false
var game_over: bool = false
var victory: bool = false

# ── Runner ──
var lane: int = 1  # 0=top, 1=middle, 2=bottom
var target_lane: int = 1
const LANE_Y = [220.0, 380.0, 540.0]
var runner_x: float = 200.0
var runner_y: float = 380.0
const RUNNER_SIZE: float = 40.0
var lane_switch_speed: float = 600.0

# ── Scrolling ──
var scroll_speed: float = 250.0
var distance: float = 0.0

# ── Gates ──
var gates: Array = []  # [{x, lane, text, correct, alive}]
const GATE_W: float = 180.0
const GATE_H: float = 100.0
var gates_active: bool = false
var waiting_for_q: bool = true
var spawn_distance: float = 0.0

# ── Ground elements ──
var ground_lines: Array = []

# ── Visual ──
var show_result: bool = false
var result_timer: float = 0.0
var result_correct: bool = false
var run_anim_timer: float = 0.0

# ── Colors ──
const C_SKY_TOP = Color(0.4, 0.7, 1.0)
const C_SKY_BOT = Color(0.7, 0.85, 1.0)
const C_GROUND = Color(0.45, 0.75, 0.35)
const C_ROAD = Color(0.55, 0.5, 0.45)
const C_LANE_LINE = Color(1, 1, 1, 0.3)
const C_RUNNER = Color(0.2, 0.5, 1.0)
const C_RUNNER_HEAD = Color(1.0, 0.85, 0.7)
const C_GATE_CORRECT = Color(0.2, 0.85, 0.3, 0.85)
const C_GATE_WRONG = Color(0.85, 0.2, 0.2, 0.85)
const C_GATE_DEFAULT = Color(0.3, 0.4, 0.8, 0.85)
const C_TEXT = Color(1, 1, 1)
const C_QUESTION = Color(1.0, 0.95, 0.7)
const C_HUD = Color(0.1, 0.1, 0.3)


func _ready() -> void:
	_load_config()
	_init_ground()
	_start_game()


func _load_config() -> void:
	var file = FileAccess.open("res://config.json", FileAccess.READ)
	if file:
		var json = JSON.new()
		json.parse(file.get_as_text())
		config = json.data
		questions = config.get("questions", [])
		file.close()


func _init_ground() -> void:
	ground_lines.clear()
	for i in range(20):
		ground_lines.append(randf_range(0, 1280))


func _start_game() -> void:
	score = 0
	lives = 3
	current_q = 0
	game_active = true
	game_over = false
	victory = false
	lane = 1
	target_lane = 1
	runner_y = LANE_Y[1]
	gates.clear()
	gates_active = false
	waiting_for_q = true
	spawn_distance = 400.0
	distance = 0.0
	_spawn_gates()


func _spawn_gates() -> void:
	gates.clear()
	if current_q >= questions.size():
		victory = true
		game_active = false
		return

	var q = questions[current_q]
	var answers: Array = [q["correct"]]
	for w in q.get("wrong", []):
		answers.append(w)

	# Trim to 3 answers (one per lane)
	while answers.size() > 3:
		answers.pop_back()
	while answers.size() < 3:
		answers.append("???")

	# Shuffle
	for i in range(answers.size() - 1, 0, -1):
		var j = randi() % (i + 1)
		var tmp = answers[i]
		answers[i] = answers[j]
		answers[j] = tmp

	# Create gates, one per lane
	for i in range(min(answers.size(), 3)):
		gates.append({
			"x": 1400.0,
			"lane": i,
			"text": answers[i],
			"correct": answers[i] == q["correct"],
			"alive": true,
		})

	gates_active = true
	waiting_for_q = false


func _process(delta: float) -> void:
	if game_over or victory:
		if Input.is_action_just_pressed("jump"):
			_start_game()
		queue_redraw()
		return

	if show_result:
		result_timer -= delta
		if result_timer <= 0:
			show_result = false
			current_q += 1
			spawn_distance = 400.0
			_spawn_gates()
		queue_redraw()
		return

	if not game_active:
		queue_redraw()
		return

	# Lane switching
	if Input.is_action_just_pressed("move_up") and lane > 0:
		target_lane = lane - 1
		lane = target_lane
	if Input.is_action_just_pressed("move_down") and lane < 2:
		target_lane = lane + 1
		lane = target_lane

	# Smooth Y movement to target lane
	var target_y = LANE_Y[lane]
	runner_y = move_toward(runner_y, target_y, lane_switch_speed * delta)

	# Scroll world
	distance += scroll_speed * delta

	# Running animation
	run_anim_timer += delta * 8

	# Update ground lines
	for i in range(ground_lines.size()):
		ground_lines[i] -= scroll_speed * delta
		if ground_lines[i] < -10:
			ground_lines[i] = 1280 + randf_range(0, 100)

	# Move gates
	for g in gates:
		if g["alive"]:
			g["x"] -= scroll_speed * delta

			# Check collision with runner
			if abs(g["x"] - runner_x) < GATE_W / 2 and g["lane"] == lane:
				g["alive"] = false
				if g["correct"]:
					score += 1
					result_correct = true
				else:
					lives -= 1
					result_correct = false
					if lives <= 0:
						game_over = true
						game_active = false
						return
				show_result = true
				result_timer = 1.5
				for g2 in gates:
					g2["alive"] = false
				break

			# Gate passed without being hit
			if g["x"] < -GATE_W:
				g["alive"] = false

	queue_redraw()


func _draw() -> void:
	# Sky gradient
	for i in range(36):
		var t = float(i) / 36.0
		var col = C_SKY_TOP.lerp(C_SKY_BOT, t)
		draw_rect(Rect2(0, i * 20, 1280, 20), col)

	# Ground
	draw_rect(Rect2(0, 620, 1280, 100), C_GROUND)

	# Road (3 lanes)
	draw_rect(Rect2(0, 160, 1280, 460), C_ROAD)

	# Lane dividers
	for y in [265, 445]:
		for x_start in range(0, 1280, 60):
			var offset = fmod(distance, 60.0)
			var lx = x_start - offset
			draw_rect(Rect2(lx, y - 2, 30, 4), C_LANE_LINE)

	if game_over:
		_draw_game_over()
		return
	if victory:
		_draw_victory()
		return

	# Gates
	for g in gates:
		if g["alive"]:
			_draw_gate(g)

	# Runner
	_draw_runner()

	# Question bar
	_draw_question()

	# HUD
	_draw_hud()

	# Result flash
	if show_result:
		_draw_result()


func _draw_runner() -> void:
	var cx = runner_x
	var cy = runner_y
	var bounce = sin(run_anim_timer) * 5

	# Body
	draw_rect(Rect2(cx - 15, cy - 25 + bounce, 30, 35), C_RUNNER)
	# Head
	draw_circle(Vector2(cx, cy - 35 + bounce), 14, C_RUNNER_HEAD)
	# Eyes
	draw_circle(Vector2(cx - 4, cy - 38 + bounce), 3, Color.WHITE)
	draw_circle(Vector2(cx + 4, cy - 38 + bounce), 3, Color.WHITE)
	draw_circle(Vector2(cx - 3, cy - 38 + bounce), 1.5, Color.BLACK)
	draw_circle(Vector2(cx + 5, cy - 38 + bounce), 1.5, Color.BLACK)

	# Legs (animated)
	var leg_angle = sin(run_anim_timer) * 20
	var leg1_end = Vector2(cx - 8 + leg_angle, cy + 20 + bounce)
	var leg2_end = Vector2(cx + 8 - leg_angle, cy + 20 + bounce)
	draw_line(Vector2(cx - 5, cy + 10 + bounce), leg1_end, C_RUNNER, 4)
	draw_line(Vector2(cx + 5, cy + 10 + bounce), leg2_end, C_RUNNER, 4)

	# Arms
	var arm_angle = cos(run_anim_timer) * 15
	draw_line(Vector2(cx - 15, cy - 15 + bounce), Vector2(cx - 25 + arm_angle, cy + bounce), C_RUNNER, 3)
	draw_line(Vector2(cx + 15, cy - 15 + bounce), Vector2(cx + 25 - arm_angle, cy + bounce), C_RUNNER, 3)


func _draw_gate(g: Dictionary) -> void:
	var gx = g["x"]
	var gy = LANE_Y[g["lane"]]
	var col = C_GATE_DEFAULT
	if show_result:
		col = C_GATE_CORRECT if g["correct"] else C_GATE_WRONG

	# Gate frame
	draw_rect(Rect2(gx - GATE_W / 2, gy - GATE_H / 2, GATE_W, GATE_H), col)
	# Border
	draw_rect(Rect2(gx - GATE_W / 2, gy - GATE_H / 2, GATE_W, 4), Color(1, 1, 1, 0.4))
	draw_rect(Rect2(gx - GATE_W / 2, gy + GATE_H / 2 - 4, GATE_W, 4), Color(1, 1, 1, 0.4))
	# Pillars
	draw_rect(Rect2(gx - GATE_W / 2, gy - GATE_H / 2, 8, GATE_H), Color(1, 1, 1, 0.3))
	draw_rect(Rect2(gx + GATE_W / 2 - 8, gy - GATE_H / 2, 8, GATE_H), Color(1, 1, 1, 0.3))

	# Text
	var font = ThemeDB.fallback_font
	var text = str(g["text"])
	var fsize = 16 if text.length() > 12 else 20
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, fsize).x
	draw_string(font, Vector2(gx - tw / 2, gy + fsize / 3), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize, C_TEXT)


func _draw_question() -> void:
	if current_q >= questions.size():
		return
	draw_rect(Rect2(0, 0, 1280, 55), Color(0.1, 0.1, 0.3, 0.85))
	var font = ThemeDB.fallback_font
	var q = questions[current_q]
	var text = q.get("question", "")
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw / 2, 36), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, C_QUESTION)
	# Lane instructions
	var hint = "W/S or Up/Down to switch lanes"
	var hw = font.get_string_size(hint, HORIZONTAL_ALIGNMENT_CENTER, -1, 14).x
	draw_string(font, Vector2(640 - hw / 2, 690), hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 1, 1, 0.5))


func _draw_hud() -> void:
	var font = ThemeDB.fallback_font
	# Score
	draw_string(font, Vector2(20, 90), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_HUD)
	# Lives
	for i in range(lives):
		draw_circle(Vector2(1220 - i * 30, 85), 10, Color(1, 0.2, 0.3))
	# Distance
	var dist_text = str(int(distance / 10)) + "m"
	draw_string(font, Vector2(600, 90), dist_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_HUD)


func _draw_result() -> void:
	var font = ThemeDB.fallback_font
	var text = "CORRECT!" if result_correct else "WRONG!"
	var col = Color(0.2, 0.9, 0.3) if result_correct else Color(0.9, 0.2, 0.2)
	draw_rect(Rect2(400, 320, 480, 80), Color(0, 0, 0, 0.7))
	var tw = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 36).x
	draw_string(font, Vector2(640 - tw / 2, 370), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 36, col)


func _draw_game_over() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.7))
	var font = ThemeDB.fallback_font
	var t1 = "GAME OVER"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 300), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, Color(0.9, 0.2, 0.2))
	var t2 = "Score: " + str(score) + "/" + str(questions.size())
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 28).x
	draw_string(font, Vector2(640 - tw2 / 2, 360), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, C_TEXT)
	var t3 = "Press SPACE to restart"
	var tw3 = font.get_string_size(t3, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw3 / 2, 420), t3, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.7, 0.8, 1.0))


func _draw_victory() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.6))
	var font = ThemeDB.fallback_font
	var t1 = "YOU WIN!"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 280), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, Color(0.2, 0.9, 0.3))
	var pct = round(float(score) / questions.size() * 100)
	var t2 = "Score: " + str(score) + "/" + str(questions.size()) + " (" + str(pct) + "%)"
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 28).x
	draw_string(font, Vector2(640 - tw2 / 2, 340), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, C_TEXT)
	var num_stars = 3 if pct >= 90 else 2 if pct >= 70 else 1 if pct >= 40 else 0
	var star_text = ""
	for i in range(num_stars):
		star_text += "★ "
	for i in range(3 - num_stars):
		star_text += "☆ "
	var tw3 = font.get_string_size(star_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 40).x
	draw_string(font, Vector2(640 - tw3 / 2, 400), star_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 40, Color(1, 0.85, 0))
	var t4 = "Press SPACE to play again"
	var tw4 = font.get_string_size(t4, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
	draw_string(font, Vector2(640 - tw4 / 2, 460), t4, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.7, 0.8, 1.0))
