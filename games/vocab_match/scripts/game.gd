extends Control

# ── Colours ──────────────────────────────────────────────────────────────────
const CARD_BACK_COLOR := Color(0.25, 0.32, 0.52)        # slate-blue back
const TERM_COLOR      := Color(0.18, 0.55, 0.78)        # blue for terms
const DEF_COLOR       := Color(0.62, 0.31, 0.70)        # purple for defs
const MATCH_BORDER    := Color(0.20, 0.78, 0.35)        # green matched ring
const BACK_PATTERN    := Color(0.35, 0.42, 0.62)        # lighter stripe accent

const CARD_WIDTH  := 155
const CARD_HEIGHT := 100
const FLIP_BACK_DELAY := 1.0

# ── Runtime state ────────────────────────────────────────────────────────────
var pairs: Array = []
var cards: Array = []            # dictionaries: {node, pair_id, side, face_up, matched}
var first_pick: Dictionary = {}
var second_pick: Dictionary = {}
var waiting_for_flip_back := false
var flip_count := 0
var matches_found := 0
var total_pairs := 0

@onready var title_label: Label          = %TitleLabel
@onready var grid: GridContainer         = %Grid
@onready var flip_counter_label: Label   = %FlipCounterLabel
@onready var star_label: Label           = %StarLabel
@onready var feedback_label: Label       = %FeedbackLabel


func _ready() -> void:
	_load_config()
	_build_cards()
	_update_hud()
	feedback_label.text = "Flip two cards to find matching pairs!"


# ── Config ───────────────────────────────────────────────────────────────────
func _load_config() -> void:
	var file := FileAccess.open("res://config.json", FileAccess.READ)
	if file == null:
		push_error("Cannot open config.json")
		return
	var json := JSON.new()
	var err := json.parse(file.get_as_text())
	file.close()
	if err != OK:
		push_error("JSON parse error: " + json.get_error_message())
		return

	var data: Dictionary = json.data
	title_label.text = data.get("title", "Vocabulary Match")
	pairs = data.get("pairs", [])
	total_pairs = pairs.size()


# ── Card creation ────────────────────────────────────────────────────────────
func _build_cards() -> void:
	# Build one entry per side (term + definition) for each pair.
	var card_data: Array = []
	for i in range(pairs.size()):
		var p: Dictionary = pairs[i]
		card_data.append({"pair_id": i, "side": "term",       "text": p["term"]})
		card_data.append({"pair_id": i, "side": "definition", "text": p["definition"]})

	# Shuffle.
	card_data.shuffle()

	for entry in card_data:
		var card_dict := _create_card_node(entry)
		cards.append(card_dict)
		grid.add_child(card_dict["node"])


func _create_card_node(entry: Dictionary) -> Dictionary:
	# Outer panel -- the card itself.
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(CARD_WIDTH, CARD_HEIGHT)

	# StyleBox for the panel.
	var style := StyleBoxFlat.new()
	style.bg_color = CARD_BACK_COLOR
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_left = 10
	style.corner_radius_bottom_right = 10
	style.border_width_left = 3
	style.border_width_right = 3
	style.border_width_top = 3
	style.border_width_bottom = 3
	style.border_color = CARD_BACK_COLOR.lightened(0.15)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 6
	style.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", style)

	# Back face -- a simple centered "?" label.
	var back_label := Label.new()
	back_label.name = "BackLabel"
	back_label.text = "?"
	back_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	back_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	back_label.add_theme_font_size_override("font_size", 32)
	back_label.add_theme_color_override("font_color", Color.WHITE)
	back_label.visible = true

	# Front face -- the term or definition text.
	var front_label := Label.new()
	front_label.name = "FrontLabel"
	front_label.text = entry["text"]
	front_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	front_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	front_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	front_label.add_theme_font_size_override("font_size", 14)
	front_label.add_theme_color_override("font_color", Color.WHITE)
	front_label.visible = false

	panel.add_child(back_label)
	panel.add_child(front_label)

	# Make clickable.
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.gui_input.connect(_on_card_input.bind(cards.size()))

	return {
		"node": panel,
		"style": style,
		"pair_id": entry["pair_id"],
		"side": entry["side"],
		"face_up": false,
		"matched": false,
	}


# ── Input handling ───────────────────────────────────────────────────────────
func _on_card_input(event: InputEvent, card_index: int) -> void:
	if not (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT):
		return
	if waiting_for_flip_back:
		return

	var card := cards[card_index]
	if card["face_up"] or card["matched"]:
		return

	_flip_up(card_index)

	if first_pick.is_empty():
		first_pick = card
		first_pick["_index"] = card_index
	else:
		second_pick = card
		second_pick["_index"] = card_index
		flip_count += 1
		_update_hud()
		_check_match()


func _flip_up(index: int) -> void:
	var card := cards[index]
	card["face_up"] = true
	var panel: PanelContainer = card["node"]
	var back_lbl: Label = panel.get_node("BackLabel")
	var front_lbl: Label = panel.get_node("FrontLabel")

	# Animate: shrink X to 0, swap visibility, grow back.
	var tween := create_tween()
	tween.tween_property(panel, "scale:x", 0.0, 0.12).set_trans(Tween.TRANS_SINE)
	tween.tween_callback(func():
		back_lbl.visible = false
		front_lbl.visible = true
		var face_color: Color = TERM_COLOR if card["side"] == "term" else DEF_COLOR
		card["style"].bg_color = face_color
		card["style"].border_color = face_color.lightened(0.2)
	)
	tween.tween_property(panel, "scale:x", 1.0, 0.12).set_trans(Tween.TRANS_SINE)


func _flip_down(index: int) -> void:
	var card := cards[index]
	card["face_up"] = false
	var panel: PanelContainer = card["node"]
	var back_lbl: Label = panel.get_node("BackLabel")
	var front_lbl: Label = panel.get_node("FrontLabel")

	var tween := create_tween()
	tween.tween_property(panel, "scale:x", 0.0, 0.12).set_trans(Tween.TRANS_SINE)
	tween.tween_callback(func():
		front_lbl.visible = false
		back_lbl.visible = true
		card["style"].bg_color = CARD_BACK_COLOR
		card["style"].border_color = CARD_BACK_COLOR.lightened(0.15)
	)
	tween.tween_property(panel, "scale:x", 1.0, 0.12).set_trans(Tween.TRANS_SINE)


# ── Match logic ──────────────────────────────────────────────────────────────
func _check_match() -> void:
	if first_pick["pair_id"] == second_pick["pair_id"] and first_pick["side"] != second_pick["side"]:
		# Match!
		first_pick["matched"] = true
		second_pick["matched"] = true
		_highlight_matched(first_pick["_index"])
		_highlight_matched(second_pick["_index"])
		matches_found += 1
		feedback_label.text = "Match found!"
		first_pick = {}
		second_pick = {}

		if matches_found == total_pairs:
			_show_score_screen()
	else:
		# No match -- flip back after delay.
		feedback_label.text = "Not a match. Try again!"
		waiting_for_flip_back = true
		var fi := first_pick["_index"] as int
		var si := second_pick["_index"] as int
		first_pick = {}
		second_pick = {}
		get_tree().create_timer(FLIP_BACK_DELAY).timeout.connect(func():
			_flip_down(fi)
			_flip_down(si)
			waiting_for_flip_back = false
		)


func _highlight_matched(index: int) -> void:
	var card := cards[index]
	card["style"].border_color = MATCH_BORDER
	card["style"].border_width_left = 4
	card["style"].border_width_right = 4
	card["style"].border_width_top = 4
	card["style"].border_width_bottom = 4

	# Slight scale-up.
	var panel: PanelContainer = card["node"]
	var tween := create_tween()
	tween.tween_property(panel, "scale", Vector2(1.06, 1.06), 0.15).set_trans(Tween.TRANS_BACK)


# ── HUD ──────────────────────────────────────────────────────────────────────
func _update_hud() -> void:
	flip_counter_label.text = "Flips: " + str(flip_count)


# ── Score screen ─────────────────────────────────────────────────────────────
func _show_score_screen() -> void:
	var star_threshold_3 := int(total_pairs * 2.5)
	var star_threshold_2 := total_pairs * 4
	var stars := 1
	if flip_count <= star_threshold_3:
		stars = 3
	elif flip_count <= star_threshold_2:
		stars = 2

	var star_text := ""
	for i in range(3):
		if i < stars:
			star_text += "★ "
		else:
			star_text += "☆ "

	star_label.text = star_text.strip_edges()
	feedback_label.text = "All matched in " + str(flip_count) + " flips!"

	# Disable further input on all cards.
	for card in cards:
		(card["node"] as PanelContainer).mouse_filter = Control.MOUSE_FILTER_IGNORE

	# Add a Play Again button.
	var btn := Button.new()
	btn.text = "Play Again"
	btn.add_theme_font_size_override("font_size", 16)
	btn.custom_minimum_size = Vector2(140, 40)
	btn.pressed.connect(_restart)
	var bottom_bar: HBoxContainer = %BottomBar
	bottom_bar.add_child(btn)


func _restart() -> void:
	get_tree().reload_current_scene()
