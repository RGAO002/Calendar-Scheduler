extends Control

# ---------------------------------------------------------------------------
# Number Line Math Game  –  Godot 4.3
# ---------------------------------------------------------------------------
# Loads rounds from config.json.  The player drags a circular marker along a
# number line and presses "Check" to submit.  Stars are awarded based on how
# close the guess is to the correct answer.
# ---------------------------------------------------------------------------

# ── Configuration ──────────────────────────────────────────────────────────
const TOLERANCE_3_STAR := 0.05   # within 5 % of range
const TOLERANCE_2_STAR := 0.15   # within 15 %
const TOLERANCE_1_STAR := 0.30   # within 30 %

# Kid-friendly palette
const COLOR_BG_TOP      := Color(0.85, 0.93, 1.0)     # light sky-blue
const COLOR_BG_BOTTOM   := Color(1.0, 1.0, 1.0)       # white
const COLOR_LINE         := Color(0.18, 0.45, 0.82)    # bright blue
const COLOR_TICK         := Color(0.25, 0.25, 0.35)    # dark slate
const COLOR_MARKER       := Color(1.0, 0.55, 0.1)     # orange
const COLOR_MARKER_RING  := Color(0.95, 0.4, 0.0)     # darker orange ring
const COLOR_CORRECT      := Color(0.2, 0.78, 0.35)    # green
const COLOR_WRONG        := Color(0.9, 0.22, 0.25)    # red
const COLOR_STAR_FILLED  := Color(1.0, 0.82, 0.0)     # gold
const COLOR_STAR_EMPTY   := Color(0.78, 0.78, 0.78)   # grey

# ── Layout constants ──────────────────────────────────────────────────────
const LINE_Y       := 240.0      # vertical centre of the number-line area
const LINE_LEFT    := 80.0       # left margin (px)
const LINE_RIGHT   := 640.0      # right margin (px)
const TICK_HALF    := 12.0       # half-height of a tick mark
const MARKER_R     := 14.0       # marker circle radius
const LINE_WIDTH   := 4.0

# ── State ──────────────────────────────────────────────────────────────────
var config: Dictionary = {}
var rounds: Array = []
var current_round: int = 0
var total_stars: int = 0
var max_stars: int = 0

var round_min: float = 0.0
var round_max: float = 1.0
var round_answer: float = 0.5

var marker_value: float = 0.5        # current player guess (world value)
var dragging: bool = false
var checked: bool = false             # has the player pressed Check?
var round_stars: int = 0
var game_over: bool = false

var correct_marker_x: float = 0.0    # pixel-x of correct answer (after check)

# ── Node references (populated in _ready) ─────────────────────────────────
@onready var prompt_label: Label       = $VBox/PromptLabel
@onready var number_line_area: Control = $VBox/NumberLineArea
@onready var btn_check: Button         = $VBox/ButtonRow/CheckButton
@onready var btn_next: Button          = $VBox/ButtonRow/NextButton
@onready var feedback_label: Label     = $VBox/FeedbackLabel
@onready var star_row: HBoxContainer   = $VBox/StarRow
@onready var bg_rect: ColorRect        = $BG


# ── Lifecycle ──────────────────────────────────────────────────────────────
func _ready() -> void:
	_load_config()
	max_stars = rounds.size() * 3

	# Background gradient (approximate with a single colour; true gradient
	# would need a shader, but this keeps things simple for kids).
	bg_rect.color = COLOR_BG_TOP

	# Wire up custom draw for the number-line area
	number_line_area.draw.connect(_draw_number_line)

	# Button signals
	btn_check.pressed.connect(_on_check_pressed)
	btn_next.pressed.connect(_on_next_pressed)

	# Style buttons
	_style_button(btn_check, Color(0.18, 0.55, 0.84))
	_style_button(btn_next, Color(0.25, 0.72, 0.45))

	# Prompt label style
	prompt_label.add_theme_font_size_override("font_size", 26)
	prompt_label.add_theme_color_override("font_color", Color(0.15, 0.15, 0.25))

	# Feedback label style
	feedback_label.add_theme_font_size_override("font_size", 20)

	_start_round()


func _process(_delta: float) -> void:
	# Redraw the number-line area every frame while dragging or after check
	number_line_area.queue_redraw()


# ── Config loading ─────────────────────────────────────────────────────────
func _load_config() -> void:
	var file := FileAccess.open("res://config.json", FileAccess.READ)
	if file == null:
		push_error("Could not open config.json")
		return
	var json := JSON.new()
	var err := json.parse(file.get_as_text())
	file.close()
	if err != OK:
		push_error("Failed to parse config.json: " + json.get_error_message())
		return
	config = json.data
	rounds = config.get("rounds", [])


# ── Round management ───────────────────────────────────────────────────────
func _start_round() -> void:
	if current_round >= rounds.size():
		_show_final_screen()
		return

	var r: Dictionary = rounds[current_round]
	round_min    = float(r.get("min", 0))
	round_max    = float(r.get("max", 1))
	round_answer = float(r.get("answer", 0.5))

	# Reset marker to the midpoint
	marker_value = (round_min + round_max) / 2.0

	checked = false
	round_stars = 0
	correct_marker_x = 0.0

	prompt_label.text = r.get("prompt", "Place the number")
	feedback_label.text = ""
	btn_check.visible = true
	btn_check.disabled = false
	btn_next.visible = false
	_update_star_display(0, false)


func _on_check_pressed() -> void:
	if checked:
		return
	checked = true

	var rng: float = round_max - round_min
	if rng == 0:
		rng = 1.0
	var distance: float = absf(marker_value - round_answer) / rng

	if distance <= TOLERANCE_3_STAR:
		round_stars = 3
	elif distance <= TOLERANCE_2_STAR:
		round_stars = 2
	elif distance <= TOLERANCE_1_STAR:
		round_stars = 1
	else:
		round_stars = 0

	total_stars += round_stars

	# Compute correct marker screen position
	var frac: float = (round_answer - round_min) / rng
	correct_marker_x = LINE_LEFT + frac * (LINE_RIGHT - LINE_LEFT)

	# Feedback text
	if round_stars == 3:
		feedback_label.text = "Perfect!"
		feedback_label.add_theme_color_override("font_color", COLOR_CORRECT)
	elif round_stars >= 1:
		feedback_label.text = "Close!  The answer is " + _fmt(round_answer)
		feedback_label.add_theme_color_override("font_color", Color(0.85, 0.6, 0.0))
	else:
		feedback_label.text = "Not quite.  The answer is " + _fmt(round_answer)
		feedback_label.add_theme_color_override("font_color", COLOR_WRONG)

	_update_star_display(round_stars, true)
	btn_check.disabled = true
	btn_next.visible = true


func _on_next_pressed() -> void:
	current_round += 1
	_start_round()


# ── Final screen ───────────────────────────────────────────────────────────
func _show_final_screen() -> void:
	game_over = true
	prompt_label.text = "Great job!"
	prompt_label.add_theme_font_size_override("font_size", 32)

	var pct: float = 0.0
	if max_stars > 0:
		pct = float(total_stars) / float(max_stars) * 100.0
	feedback_label.text = "You earned %d out of %d stars! (%d%%)" % [total_stars, max_stars, int(pct)]
	feedback_label.add_theme_color_override("font_color", COLOR_CORRECT)

	btn_check.visible = false
	btn_next.visible = false
	_update_star_display_final()


# ── Drawing (number line, ticks, marker) ───────────────────────────────────
# Connected to NumberLineArea's draw signal in _ready().

func _draw_number_line() -> void:
	if game_over:
		return

	var canvas: Control = number_line_area

	# ── Number line (horizontal) ──
	canvas.draw_line(
		Vector2(LINE_LEFT, LINE_Y),
		Vector2(LINE_RIGHT, LINE_Y),
		COLOR_LINE, LINE_WIDTH, true
	)

	# ── Tick marks & labels ──
	var rng: float = round_max - round_min
	if rng == 0:
		rng = 1.0
	var tick_count: int = _choose_tick_count(rng)

	for i in range(tick_count + 1):
		var frac: float = float(i) / float(tick_count)
		var px: float = LINE_LEFT + frac * (LINE_RIGHT - LINE_LEFT)
		# Tick line
		canvas.draw_line(
			Vector2(px, LINE_Y - TICK_HALF),
			Vector2(px, LINE_Y + TICK_HALF),
			COLOR_TICK, 2.0
		)
		# Tick label
		var val: float = round_min + frac * rng
		var label_text: String = _fmt(val)
		canvas.draw_string(
			ThemeDB.fallback_font,
			Vector2(px - 12, LINE_Y + TICK_HALF + 18),
			label_text,
			HORIZONTAL_ALIGNMENT_CENTER, -1, 14, COLOR_TICK
		)

	# ── Correct-answer marker (only after check) ──
	if checked:
		# Vertical line at correct position
		canvas.draw_line(
			Vector2(correct_marker_x, LINE_Y - 30),
			Vector2(correct_marker_x, LINE_Y + 30),
			COLOR_CORRECT, 3.0
		)
		# Small diamond
		var d := 8.0
		var pts: PackedVector2Array = PackedVector2Array([
			Vector2(correct_marker_x, LINE_Y - d),
			Vector2(correct_marker_x + d, LINE_Y),
			Vector2(correct_marker_x, LINE_Y + d),
			Vector2(correct_marker_x - d, LINE_Y),
		])
		canvas.draw_colored_polygon(pts, COLOR_CORRECT)

	# ── Player marker (draggable circle) ──
	var marker_frac: float = (marker_value - round_min) / rng
	var marker_x: float = LINE_LEFT + marker_frac * (LINE_RIGHT - LINE_LEFT)

	# Shadow
	canvas.draw_circle(Vector2(marker_x + 2, LINE_Y + 2), MARKER_R, Color(0, 0, 0, 0.18))
	# Outer ring
	canvas.draw_circle(Vector2(marker_x, LINE_Y), MARKER_R + 2, COLOR_MARKER_RING)
	# Inner fill
	canvas.draw_circle(Vector2(marker_x, LINE_Y), MARKER_R, COLOR_MARKER)

	# Small label above marker showing current value
	if not checked:
		var val_text: String = _fmt(marker_value)
		canvas.draw_string(
			ThemeDB.fallback_font,
			Vector2(marker_x - 16, LINE_Y - MARKER_R - 8),
			val_text,
			HORIZONTAL_ALIGNMENT_CENTER, -1, 14, COLOR_MARKER_RING
		)


# ── Input handling (drag the marker) ──────────────────────────────────────
func _input(event: InputEvent) -> void:
	if checked or game_over:
		return

	if event is InputEventMouseButton:
		var mb: InputEventMouseButton = event
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				if _is_near_marker(mb.position):
					dragging = true
			else:
				dragging = false

	elif event is InputEventMouseMotion and dragging:
		var mm: InputEventMouseMotion = event
		_move_marker_to_x(mm.position.x)

	# Touch support (same logic)
	if event is InputEventScreenTouch:
		var st: InputEventScreenTouch = event
		if st.pressed:
			if _is_near_marker(st.position):
				dragging = true
		else:
			dragging = false

	elif event is InputEventScreenDrag and dragging:
		var sd: InputEventScreenDrag = event
		_move_marker_to_x(sd.position.x)


func _is_near_marker(pos: Vector2) -> bool:
	var rng: float = round_max - round_min
	if rng == 0:
		rng = 1.0
	var marker_frac: float = (marker_value - round_min) / rng
	var marker_x: float = LINE_LEFT + marker_frac * (LINE_RIGHT - LINE_LEFT)
	var marker_screen := Vector2(marker_x, LINE_Y)
	# Generous hit area for kids
	return pos.distance_to(marker_screen) < MARKER_R * 3.0


func _move_marker_to_x(px: float) -> void:
	px = clampf(px, LINE_LEFT, LINE_RIGHT)
	var frac: float = (px - LINE_LEFT) / (LINE_RIGHT - LINE_LEFT)
	marker_value = round_min + frac * (round_max - round_min)
	# Snap to 3 decimal places to avoid floating-point noise in display
	marker_value = snappedf(marker_value, 0.001)


# ── Star display helpers ──────────────────────────────────────────────────
func _update_star_display(count: int, show: bool) -> void:
	# Remove old stars
	for c in star_row.get_children():
		c.queue_free()

	if not show:
		return

	for i in range(3):
		var lbl := Label.new()
		lbl.add_theme_font_size_override("font_size", 32)
		if i < count:
			lbl.text = "★"
			lbl.add_theme_color_override("font_color", COLOR_STAR_FILLED)
		else:
			lbl.text = "☆"
			lbl.add_theme_color_override("font_color", COLOR_STAR_EMPTY)
		star_row.add_child(lbl)


func _update_star_display_final() -> void:
	for c in star_row.get_children():
		c.queue_free()

	# Show total stars earned as filled, rest as empty
	for i in range(max_stars):
		var lbl := Label.new()
		lbl.add_theme_font_size_override("font_size", 28)
		if i < total_stars:
			lbl.text = "★"
			lbl.add_theme_color_override("font_color", COLOR_STAR_FILLED)
		else:
			lbl.text = "☆"
			lbl.add_theme_color_override("font_color", COLOR_STAR_EMPTY)
		star_row.add_child(lbl)


# ── Utilities ──────────────────────────────────────────────────────────────
func _choose_tick_count(rng: float) -> int:
	# Pick a sensible number of ticks based on range
	if rng <= 1.0:
		return 4
	elif rng <= 3.0:
		return int(rng)       # e.g. 0..3 → ticks at 0,1,2,3
	elif rng <= 10.0:
		return int(rng)       # 0..10 → ticks at every integer
	else:
		return 10


func _fmt(val: float) -> String:
	# Format a number nicely: integers without decimals, others to 2dp
	if absf(val - roundf(val)) < 0.001:
		return str(int(roundf(val)))
	else:
		return "%.2f" % val


func _style_button(btn: Button, base_color: Color) -> void:
	# Apply a kid-friendly rounded style to a button
	var style := StyleBoxFlat.new()
	style.bg_color = base_color
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_left = 10
	style.corner_radius_bottom_right = 10
	style.content_margin_left = 16.0
	style.content_margin_right = 16.0
	style.content_margin_top = 8.0
	style.content_margin_bottom = 8.0
	btn.add_theme_stylebox_override("normal", style)

	var hover_style := style.duplicate()
	hover_style.bg_color = base_color.lightened(0.15)
	btn.add_theme_stylebox_override("hover", hover_style)

	var pressed_style := style.duplicate()
	pressed_style.bg_color = base_color.darkened(0.1)
	btn.add_theme_stylebox_override("pressed", pressed_style)

	btn.add_theme_font_size_override("font_size", 18)
	btn.add_theme_color_override("font_color", Color.WHITE)
