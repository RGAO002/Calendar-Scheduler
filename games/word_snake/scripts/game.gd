extends Node2D
## Word Snake — Classic snake game where you eat letters in order to spell words.
##
## A word + hint are shown. Letters are scattered on the grid.
## Eat them in the correct order to spell the word.
## Eating a wrong letter = lose a life. Spelling the word = next word!
## Snake grows with each correct letter. Don't hit yourself!

# ── Grid ──
const GRID_COLS: int = 32
const GRID_ROWS: int = 18
const CELL_SIZE: float = 40.0
const GRID_OFFSET_X: float = 0.0
const GRID_OFFSET_Y: float = 0.0

# ── Config ──
var config: Dictionary = {}
var words: Array = []
var current_word_idx: int = 0
var current_word: String = ""
var current_hint: String = ""
var next_letter_idx: int = 0
var score: int = 0
var lives: int = 3

# ── Snake ──
var snake: Array = []  # Array of Vector2i grid positions [head, ..., tail]
var direction: Vector2i = Vector2i(1, 0)
var next_direction: Vector2i = Vector2i(1, 0)
var move_timer: float = 0.0
const MOVE_INTERVAL: float = 0.12

# ── Letters on grid ──
var letter_cells: Array = []  # [{pos: Vector2i, letter: String, correct_idx: int}]

# ── Game state ──
var game_active: bool = false
var game_over: bool = false
var victory: bool = false
var show_result: bool = false
var result_timer: float = 0.0
var result_text: String = ""
var result_correct: bool = false
var collected_letters: String = ""

# ── Visual ──
var bg_pattern_offset: float = 0.0

# ── Colors ──
const C_BG = Color(0.12, 0.12, 0.18)
const C_GRID = Color(0.16, 0.16, 0.22)
const C_GRID_LINE = Color(0.2, 0.2, 0.28)
const C_SNAKE_HEAD = Color(0.2, 0.8, 0.3)
const C_SNAKE_BODY = Color(0.15, 0.65, 0.25)
const C_SNAKE_EYE = Color(1, 1, 1)
const C_LETTER_NEXT = Color(1.0, 0.85, 0.2)
const C_LETTER_OTHER = Color(0.5, 0.5, 0.6)
const C_LETTER_WRONG = Color(0.8, 0.3, 0.3)
const C_TEXT = Color(1, 1, 1)
const C_HINT = Color(0.7, 0.8, 1.0)
const C_CORRECT = Color(0.2, 0.9, 0.3)
const C_WRONG = Color(0.9, 0.2, 0.2)
const C_GOLD = Color(1, 0.85, 0.2)
const C_WORD_DONE = Color(0.3, 0.9, 0.4)
const C_WORD_PENDING = Color(0.4, 0.4, 0.5)


func _ready() -> void:
	_load_config()
	_start_game()


func _load_config() -> void:
	var file = FileAccess.open("res://config.json", FileAccess.READ)
	if file:
		var json = JSON.new()
		json.parse(file.get_as_text())
		config = json.data
		words = config.get("words", [])
		file.close()


func _start_game() -> void:
	current_word_idx = 0
	score = 0
	lives = 3
	game_active = true
	game_over = false
	victory = false
	collected_letters = ""
	_start_word()


func _start_word() -> void:
	if current_word_idx >= words.size():
		victory = true
		game_active = false
		return

	var w = words[current_word_idx]
	current_word = w.get("word", "").to_upper()
	current_hint = w.get("hint", "")
	next_letter_idx = 0
	collected_letters = ""

	# Reset snake (center of grid, length 3)
	snake.clear()
	var start_x = GRID_COLS / 2
	var start_y = GRID_ROWS / 2
	snake.append(Vector2i(start_x, start_y))
	snake.append(Vector2i(start_x - 1, start_y))
	snake.append(Vector2i(start_x - 2, start_y))
	direction = Vector2i(1, 0)
	next_direction = Vector2i(1, 0)

	# Place letters
	_place_letters()


func _place_letters() -> void:
	letter_cells.clear()
	var used_positions: Array = []
	for s in snake:
		used_positions.append(s)

	# Place each letter of the word
	for i in range(current_word.length()):
		var letter = current_word[i]
		var pos = _random_free_pos(used_positions)
		letter_cells.append({
			"pos": pos,
			"letter": letter,
			"correct_idx": i,
			"alive": true,
		})
		used_positions.append(pos)

	# Place some decoy letters
	var decoys = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	var num_decoys = min(8, GRID_COLS * GRID_ROWS / 10)
	for i in range(num_decoys):
		var dl = decoys[randi() % decoys.length()]
		var pos = _random_free_pos(used_positions)
		letter_cells.append({
			"pos": pos,
			"letter": dl,
			"correct_idx": -1,  # decoy
			"alive": true,
		})
		used_positions.append(pos)


func _random_free_pos(used: Array) -> Vector2i:
	var attempts = 0
	while attempts < 200:
		var pos = Vector2i(randi() % GRID_COLS, randi() % GRID_ROWS)
		if pos not in used:
			return pos
		attempts += 1
	return Vector2i(randi() % GRID_COLS, randi() % GRID_ROWS)


func _process(delta: float) -> void:
	if game_over or victory:
		if Input.is_action_just_pressed("move_up") or Input.is_action_just_pressed("move_down"):
			_start_game()
		queue_redraw()
		return

	if show_result:
		result_timer -= delta
		if result_timer <= 0:
			show_result = false
		queue_redraw()
		return

	if not game_active:
		queue_redraw()
		return

	# Direction input (prevent 180-degree turns)
	if Input.is_action_just_pressed("move_up") and direction != Vector2i(0, 1):
		next_direction = Vector2i(0, -1)
	elif Input.is_action_just_pressed("move_down") and direction != Vector2i(0, -1):
		next_direction = Vector2i(0, 1)
	elif Input.is_action_just_pressed("move_left") and direction != Vector2i(1, 0):
		next_direction = Vector2i(-1, 0)
	elif Input.is_action_just_pressed("move_right") and direction != Vector2i(-1, 0):
		next_direction = Vector2i(1, 0)

	# Move snake
	move_timer += delta
	if move_timer >= MOVE_INTERVAL:
		move_timer = 0.0
		_move_snake()

	queue_redraw()


func _move_snake() -> void:
	direction = next_direction
	var head = snake[0]
	var new_head = head + direction

	# Wrap around
	new_head.x = posmod(new_head.x, GRID_COLS)
	new_head.y = posmod(new_head.y, GRID_ROWS)

	# Check self-collision
	if new_head in snake:
		lives -= 1
		if lives <= 0:
			game_over = true
			game_active = false
		else:
			show_result = true
			result_timer = 1.0
			result_text = "Hit yourself! -1 life"
			result_correct = false
			# Reset snake position
			_start_word()
		return

	# Check letter collision
	var ate_letter = false
	var ate_correct = false
	for lc in letter_cells:
		if not lc["alive"]:
			continue
		if lc["pos"] == new_head:
			lc["alive"] = false
			if lc["correct_idx"] == next_letter_idx:
				# Correct letter!
				ate_correct = true
				collected_letters += lc["letter"]
				next_letter_idx += 1
				score += 1
				ate_letter = true

				# Check if word complete
				if next_letter_idx >= current_word.length():
					show_result = true
					result_timer = 1.5
					result_text = "Spelled: " + current_word + "!"
					result_correct = true
					current_word_idx += 1
					# Delay starting next word
					await get_tree().create_timer(1.5).timeout
					_start_word()
					return
			else:
				# Wrong letter
				lives -= 1
				show_result = true
				result_timer = 1.0
				result_text = "Wrong letter!"
				result_correct = false
				if lives <= 0:
					game_over = true
					game_active = false
					return
			break

	# Move snake
	snake.insert(0, new_head)
	if not ate_correct:
		snake.pop_back()  # Remove tail (don't grow)
	# If correct, keep tail (snake grows)


func _draw() -> void:
	# Background
	draw_rect(Rect2(0, 0, 1280, 720), C_BG)

	# Grid
	_draw_grid()

	# Letters
	_draw_letters()

	# Snake
	_draw_snake()

	# HUD
	_draw_hud()

	# Result flash
	if show_result:
		_draw_result()

	if game_over:
		_draw_game_over()
	if victory:
		_draw_victory()


func _draw_grid() -> void:
	# Grid lines
	for x in range(GRID_COLS + 1):
		var px = GRID_OFFSET_X + x * CELL_SIZE
		draw_line(Vector2(px, GRID_OFFSET_Y), Vector2(px, GRID_OFFSET_Y + GRID_ROWS * CELL_SIZE), C_GRID_LINE, 1)
	for y in range(GRID_ROWS + 1):
		var py = GRID_OFFSET_Y + y * CELL_SIZE
		draw_line(Vector2(GRID_OFFSET_X, py), Vector2(GRID_OFFSET_X + GRID_COLS * CELL_SIZE, py), C_GRID_LINE, 1)


func _draw_letters() -> void:
	var font = ThemeDB.fallback_font
	for lc in letter_cells:
		if not lc["alive"]:
			continue
		var px = GRID_OFFSET_X + lc["pos"].x * CELL_SIZE
		var py = GRID_OFFSET_Y + lc["pos"].y * CELL_SIZE

		var is_next = lc["correct_idx"] == next_letter_idx
		var is_correct_future = lc["correct_idx"] > next_letter_idx and lc["correct_idx"] >= 0
		var col = C_LETTER_NEXT if is_next else (C_LETTER_OTHER if is_correct_future or lc["correct_idx"] >= 0 else C_LETTER_WRONG)

		# Background circle
		var center = Vector2(px + CELL_SIZE / 2, py + CELL_SIZE / 2)
		var bg_col = Color(col.r, col.g, col.b, 0.25)
		draw_circle(center, CELL_SIZE / 2 - 2, bg_col)

		# Highlight next letter
		if is_next:
			draw_circle(center, CELL_SIZE / 2 - 1, Color(C_LETTER_NEXT.r, C_LETTER_NEXT.g, C_LETTER_NEXT.b, 0.15))
			# Pulsing border
			_draw_circle_outline(center, CELL_SIZE / 2 - 2, C_LETTER_NEXT, 2)

		# Letter text
		var letter = lc["letter"]
		var tw = font.get_string_size(letter, HORIZONTAL_ALIGNMENT_CENTER, -1, 22).x
		draw_string(font, Vector2(center.x - tw / 2, center.y + 8), letter, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, col)


func _draw_snake() -> void:
	for i in range(snake.size() - 1, -1, -1):
		var seg = snake[i]
		var px = GRID_OFFSET_X + seg.x * CELL_SIZE
		var py = GRID_OFFSET_Y + seg.y * CELL_SIZE
		var center = Vector2(px + CELL_SIZE / 2, py + CELL_SIZE / 2)

		if i == 0:
			# Head
			draw_circle(center, CELL_SIZE / 2 - 1, C_SNAKE_HEAD)
			# Eyes based on direction
			var eye_off1 = Vector2.ZERO
			var eye_off2 = Vector2.ZERO
			match direction:
				Vector2i(1, 0):  # right
					eye_off1 = Vector2(6, -6)
					eye_off2 = Vector2(6, 6)
				Vector2i(-1, 0):  # left
					eye_off1 = Vector2(-6, -6)
					eye_off2 = Vector2(-6, 6)
				Vector2i(0, -1):  # up
					eye_off1 = Vector2(-6, -6)
					eye_off2 = Vector2(6, -6)
				Vector2i(0, 1):  # down
					eye_off1 = Vector2(-6, 6)
					eye_off2 = Vector2(6, 6)
			draw_circle(center + eye_off1, 4, C_SNAKE_EYE)
			draw_circle(center + eye_off2, 4, C_SNAKE_EYE)
			draw_circle(center + eye_off1 + Vector2(direction.x, direction.y) * 1.5, 2, Color.BLACK)
			draw_circle(center + eye_off2 + Vector2(direction.x, direction.y) * 1.5, 2, Color.BLACK)
		else:
			# Body - slightly smaller
			var body_size = CELL_SIZE / 2 - 3
			draw_circle(center, body_size, C_SNAKE_BODY)
			# Stripe pattern
			if i % 2 == 0:
				draw_circle(center, body_size - 4, Color(C_SNAKE_BODY.r + 0.08, C_SNAKE_BODY.g + 0.08, C_SNAKE_BODY.b))


func _draw_hud() -> void:
	var font = ThemeDB.fallback_font

	# Word display at top
	var word_y = GRID_OFFSET_Y + GRID_ROWS * CELL_SIZE + 5
	var word_x = 20.0

	# Title
	draw_string(font, Vector2(word_x, word_y + 18), "Spell: ", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_HINT)

	# Letters of the word (collected = green, next = gold, remaining = gray)
	var lx = word_x + 70
	for i in range(current_word.length()):
		var letter = current_word[i]
		var col = C_WORD_DONE
		if i >= next_letter_idx:
			col = C_GOLD if i == next_letter_idx else C_WORD_PENDING

		# Letter box
		draw_rect(Rect2(lx, word_y, 30, 30), Color(col.r, col.g, col.b, 0.2))
		var tw = font.get_string_size(letter, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
		if i < next_letter_idx:
			draw_string(font, Vector2(lx + 15 - tw / 2, word_y + 22), letter, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, col)
		else:
			draw_string(font, Vector2(lx + 15 - tw / 2, word_y + 22), "?", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, col)
		lx += 35

	# Hint
	draw_string(font, Vector2(lx + 20, word_y + 18), "Hint: " + current_hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_HINT)

	# Lives + Score
	var info_y = word_y + 35
	draw_string(font, Vector2(20, info_y + 15), "Score: " + str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, C_GOLD)
	for i in range(lives):
		draw_circle(Vector2(200 + i * 25, info_y + 10), 8, Color(1, 0.2, 0.3))
	draw_string(font, Vector2(300, info_y + 15),
		"Word " + str(current_word_idx + 1) + "/" + str(words.size()),
		HORIZONTAL_ALIGNMENT_LEFT, -1, 16, C_TEXT)
	draw_string(font, Vector2(500, info_y + 15), "WASD to move | Eat letters in order!", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.5, 0.5, 0.6))


func _draw_result() -> void:
	var font = ThemeDB.fallback_font
	var col = C_CORRECT if result_correct else C_WRONG
	draw_rect(Rect2(400, 300, 480, 60), Color(0, 0, 0, 0.8))
	var tw = font.get_string_size(result_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 28).x
	draw_string(font, Vector2(640 - tw / 2, 340), result_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, col)


func _draw_game_over() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.75))
	var font = ThemeDB.fallback_font
	var t1 = "GAME OVER"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 300), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_WRONG)
	var t2 = "Words spelled: " + str(current_word_idx) + "/" + str(words.size())
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 360), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	var t3 = "Press W or S to restart"
	var tw3 = font.get_string_size(t3, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw3 / 2, 420), t3, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _draw_victory() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.6))
	var font = ThemeDB.fallback_font
	var t1 = "ALL WORDS SPELLED!"
	var tw1 = font.get_string_size(t1, HORIZONTAL_ALIGNMENT_CENTER, -1, 48).x
	draw_string(font, Vector2(640 - tw1 / 2, 260), t1, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, C_CORRECT)
	var pct = round(float(score) / _total_letters() * 100) if _total_letters() > 0 else 100
	var t2 = "Letters collected: " + str(score) + " | Accuracy: " + str(pct) + "%"
	var tw2 = font.get_string_size(t2, HORIZONTAL_ALIGNMENT_CENTER, -1, 24).x
	draw_string(font, Vector2(640 - tw2 / 2, 330), t2, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, C_TEXT)
	var num_stars = 3 if lives >= 3 else 2 if lives >= 2 else 1
	var star_text = ""
	for i in range(num_stars):
		star_text += "★ "
	for i in range(3 - num_stars):
		star_text += "☆ "
	var tw3 = font.get_string_size(star_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 40).x
	draw_string(font, Vector2(640 - tw3 / 2, 390), star_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 40, C_GOLD)
	var t4 = "Press W or S to play again"
	var tw4 = font.get_string_size(t4, HORIZONTAL_ALIGNMENT_CENTER, -1, 20).x
	draw_string(font, Vector2(640 - tw4 / 2, 450), t4, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, C_GOLD)


func _total_letters() -> int:
	var total = 0
	for w in words:
		total += w.get("word", "").length()
	return total


func _draw_circle_outline(center: Vector2, radius: float, color: Color, width: float = 1.0) -> void:
	var pts = 24
	for i in range(pts):
		var a1 = i * TAU / pts
		var a2 = (i + 1) * TAU / pts
		draw_line(
			center + Vector2(cos(a1), sin(a1)) * radius,
			center + Vector2(cos(a2), sin(a2)) * radius,
			color, width
		)
