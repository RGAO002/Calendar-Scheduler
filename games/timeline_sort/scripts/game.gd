extends Control

# ── Colours ──────────────────────────────────────────────────────────────────
const BG_COLOR          := Color(0.96, 0.93, 0.87)       # warm parchment
const CARD_BG           := Color(0.28, 0.42, 0.62)       # steel-blue card
const CARD_BORDER       := Color(0.38, 0.52, 0.72)       # lighter blue border
const SLOT_BG           := Color(0.88, 0.85, 0.78)       # empty slot beige
const SLOT_BORDER       := Color(0.70, 0.65, 0.55)       # slot outline
const CORRECT_COLOR     := Color(0.20, 0.72, 0.35)       # green correct
const WRONG_COLOR       := Color(0.85, 0.22, 0.22)       # red wrong
const TIMELINE_COLOR    := Color(0.45, 0.35, 0.25)       # brown timeline line
const STAR_ON_COLOR     := Color(1.0, 0.82, 0.15)        # gold star
const STAR_OFF_COLOR    := Color(0.70, 0.68, 0.62)       # grey star

const CARD_WIDTH   := 105
const CARD_HEIGHT  := 60
const SLOT_WIDTH   := 105
const SLOT_HEIGHT  := 80

# ── Runtime state ────────────────────────────────────────────────────────────
var events: Array = []            # parsed event dicts from config
var pool_cards: Array = []        # {node, event_index, original_event}
var slot_nodes: Array = []        # PanelContainer nodes for timeline slots
var slot_contents: Array = []     # index into pool_cards or -1 if empty
var dragged_card_index := -1      # which pool card is being dragged
var drag_offset := Vector2.ZERO
var drag_source_slot := -1        # slot index card was dragged FROM (-1 = from pool)
var checked := false              # has player pressed Check Order?
var correct_count := 0

@onready var title_label: Label         = %TitleLabel
@onready var timeline_area: Control     = %TimelineArea
@onready var card_pool: HBoxContainer   = %CardPool
@onready var button_bar: HBoxContainer  = %ButtonBar
@onready var feedback_label: Label      = %FeedbackLabel
@onready var star_bar: HBoxContainer    = %StarBar
@onready var check_btn: Button          = %CheckBtn
@onready var play_again_btn: Button     = %PlayAgainBtn


func _ready() -> void:
	_load_config()
	_build_timeline_slots()
	_build_pool_cards()
	_update_feedback("Drag event cards onto the timeline in order!")
	play_again_btn.visible = false
	check_btn.pressed.connect(_on_check_pressed)
	play_again_btn.pressed.connect(_restart)


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
	title_label.text = data.get("title", "Timeline Sort")
	events = data.get("events", [])


# ── Timeline slots (top area) ───────────────────────────────────────────────
func _build_timeline_slots() -> void:
	slot_nodes.clear()
	slot_contents.clear()

	# Remove old children.
	for child in timeline_area.get_children():
		child.queue_free()

	var count := events.size()
	var total_width := count * SLOT_WIDTH + (count - 1) * 8
	var start_x := (timeline_area.size.x - total_width) / 2.0
	var slot_y := 25.0

	# Draw a horizontal timeline line using a ColorRect.
	var line := ColorRect.new()
	line.color = TIMELINE_COLOR
	line.position = Vector2(start_x - 10, slot_y + SLOT_HEIGHT / 2.0 - 2)
	line.size = Vector2(total_width + 20, 4)
	timeline_area.add_child(line)

	for i in range(count):
		var slot := PanelContainer.new()
		slot.custom_minimum_size = Vector2(SLOT_WIDTH, SLOT_HEIGHT)
		slot.size = Vector2(SLOT_WIDTH, SLOT_HEIGHT)
		slot.position = Vector2(start_x + i * (SLOT_WIDTH + 8), slot_y)

		var style := StyleBoxFlat.new()
		style.bg_color = SLOT_BG
		style.corner_radius_top_left = 6
		style.corner_radius_top_right = 6
		style.corner_radius_bottom_left = 6
		style.corner_radius_bottom_right = 6
		style.border_width_left = 2
		style.border_width_right = 2
		style.border_width_top = 2
		style.border_width_bottom = 2
		style.border_color = SLOT_BORDER
		style.content_margin_left = 4
		style.content_margin_right = 4
		style.content_margin_top = 4
		style.content_margin_bottom = 4
		slot.add_theme_stylebox_override("panel", style)

		# Slot number label.
		var num_label := Label.new()
		num_label.name = "NumLabel"
		num_label.text = str(i + 1)
		num_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		num_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		num_label.add_theme_font_size_override("font_size", 14)
		num_label.add_theme_color_override("font_color", SLOT_BORDER)
		slot.add_child(num_label)

		# Year label (hidden until check).
		var year_label := Label.new()
		year_label.name = "YearLabel"
		year_label.text = ""
		year_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		year_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		year_label.add_theme_font_size_override("font_size", 11)
		year_label.add_theme_color_override("font_color", TIMELINE_COLOR)
		year_label.visible = false
		slot.add_child(year_label)

		timeline_area.add_child(slot)
		slot_nodes.append(slot)
		slot_contents.append(-1)


# ── Pool cards (bottom area) ────────────────────────────────────────────────
func _build_pool_cards() -> void:
	pool_cards.clear()

	# Remove old children.
	for child in card_pool.get_children():
		child.queue_free()

	# Create shuffled indices.
	var indices: Array = []
	for i in range(events.size()):
		indices.append(i)
	indices.shuffle()

	for idx in indices:
		var ev: Dictionary = events[idx]
		var card := _create_card(ev["label"], ev.get("hint", ""))
		var card_dict := {
			"node": card,
			"event_index": idx,
			"original_event": ev,
			"in_pool": true,
			"slot_index": -1,
		}
		pool_cards.append(card_dict)
		card_pool.add_child(card)


func _create_card(label_text: String, hint_text: String) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(CARD_WIDTH, CARD_HEIGHT)

	var style := StyleBoxFlat.new()
	style.bg_color = CARD_BG
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_left = 8
	style.corner_radius_bottom_right = 8
	style.border_width_left = 2
	style.border_width_right = 2
	style.border_width_top = 2
	style.border_width_bottom = 2
	style.border_color = CARD_BORDER
	style.content_margin_left = 6
	style.content_margin_right = 6
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.name = "VBox"

	var title := Label.new()
	title.name = "TitleLabel"
	title.text = label_text
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", 11)
	title.add_theme_color_override("font_color", Color.WHITE)

	var hint := Label.new()
	hint.name = "HintLabel"
	hint.text = hint_text
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_font_size_override("font_size", 9)
	hint.add_theme_color_override("font_color", Color(0.82, 0.85, 0.92))

	vbox.add_child(title)
	vbox.add_child(hint)
	panel.add_child(vbox)

	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	return panel


# ── Drag & Drop via _input ──────────────────────────────────────────────────
func _input(event: InputEvent) -> void:
	if checked:
		return

	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_try_pick_up(event.global_position)
		else:
			_try_drop(event.global_position)

	elif event is InputEventMouseMotion and dragged_card_index >= 0:
		var card_node: PanelContainer = pool_cards[dragged_card_index]["node"]
		card_node.global_position = event.global_position - drag_offset


func _try_pick_up(pos: Vector2) -> void:
	# First check if clicking a card that is sitting in a slot.
	for i in range(pool_cards.size()):
		var card: Dictionary = pool_cards[i]
		var node: PanelContainer = card["node"]
		if not node.visible:
			continue
		var rect := Rect2(node.global_position, node.size)
		if rect.has_point(pos):
			dragged_card_index = i
			drag_offset = pos - node.global_position

			# If card was in a slot, free that slot.
			if card["slot_index"] >= 0:
				drag_source_slot = card["slot_index"]
				slot_contents[card["slot_index"]] = -1
				_reset_slot_style(card["slot_index"])
				card["slot_index"] = -1
			else:
				drag_source_slot = -1

			# Reparent to root so it draws on top.
			card["in_pool"] = false
			node.reparent(self)
			node.z_index = 10

			# Enlarge slightly while dragging.
			var tween := create_tween()
			tween.tween_property(node, "scale", Vector2(1.08, 1.08), 0.1)
			return


func _try_drop(pos: Vector2) -> void:
	if dragged_card_index < 0:
		return

	var card: Dictionary = pool_cards[dragged_card_index]
	var card_node: PanelContainer = card["node"]

	# Shrink back to normal.
	var tween := create_tween()
	tween.tween_property(card_node, "scale", Vector2.ONE, 0.1)

	# Check if dropped onto a timeline slot.
	var placed := false
	for i in range(slot_nodes.size()):
		var slot: PanelContainer = slot_nodes[i]
		var slot_rect := Rect2(slot.global_position, slot.size)
		if slot_rect.has_point(pos):
			if slot_contents[i] == -1:
				# Place card into slot.
				_place_card_in_slot(dragged_card_index, i)
				placed = true
			elif slot_contents[i] != dragged_card_index:
				# Slot occupied -- swap the existing card back to pool.
				var existing_idx: int = slot_contents[i]
				_return_card_to_pool(existing_idx)
				_place_card_in_slot(dragged_card_index, i)
				placed = true
			break

	if not placed:
		# Return to pool.
		_return_card_to_pool(dragged_card_index)

	dragged_card_index = -1
	drag_source_slot = -1


func _place_card_in_slot(card_idx: int, slot_idx: int) -> void:
	var card: Dictionary = pool_cards[card_idx]
	var card_node: PanelContainer = card["node"]
	var slot: PanelContainer = slot_nodes[slot_idx]

	slot_contents[slot_idx] = card_idx
	card["slot_index"] = slot_idx
	card["in_pool"] = false

	# Position card centered on slot.
	card_node.reparent(self)
	card_node.z_index = 5
	var target_pos := slot.global_position + (slot.size - card_node.size) / 2.0
	var tween := create_tween()
	tween.tween_property(card_node, "global_position", target_pos, 0.15).set_trans(Tween.TRANS_QUAD)

	# Hide slot number.
	var num_label: Label = slot.get_node("NumLabel")
	num_label.visible = false


func _return_card_to_pool(card_idx: int) -> void:
	var card: Dictionary = pool_cards[card_idx]
	var card_node: PanelContainer = card["node"]

	# If it was in a slot, free that slot.
	if card["slot_index"] >= 0:
		slot_contents[card["slot_index"]] = -1
		_reset_slot_style(card["slot_index"])
		var num_label: Label = slot_nodes[card["slot_index"]].get_node("NumLabel")
		num_label.visible = true
		card["slot_index"] = -1

	card["in_pool"] = true
	card_node.z_index = 0
	card_node.reparent(card_pool)

	# Reset card border to default.
	var style: StyleBoxFlat = card_node.get_theme_stylebox("panel")
	style.border_color = CARD_BORDER


func _reset_slot_style(slot_idx: int) -> void:
	var slot: PanelContainer = slot_nodes[slot_idx]
	var style: StyleBoxFlat = slot.get_theme_stylebox("panel")
	style.border_color = SLOT_BORDER
	style.bg_color = SLOT_BG

	var num_label: Label = slot.get_node("NumLabel")
	num_label.visible = true

	var year_label: Label = slot.get_node("YearLabel")
	year_label.visible = false


# ── Check Order ─────────────────────────────────────────────────────────────
func _on_check_pressed() -> void:
	# Require all slots filled.
	for i in range(slot_contents.size()):
		if slot_contents[i] == -1:
			_update_feedback("Place all cards on the timeline first!")
			return

	checked = true
	correct_count = 0

	# Build the correct order: events sorted by year, preserving config order
	# for same-year events.
	var sorted_indices: Array = []
	for i in range(events.size()):
		sorted_indices.append(i)
	sorted_indices.sort_custom(func(a: int, b: int) -> bool:
		return events[a]["year"] < events[b]["year"]
	)

	# Check each slot.
	for slot_idx in range(slot_nodes.size()):
		var card_idx: int = slot_contents[slot_idx]
		var card: Dictionary = pool_cards[card_idx]
		var event_index: int = card["event_index"]
		var expected_index: int = sorted_indices[slot_idx]

		var card_node: PanelContainer = card["node"]
		var card_style: StyleBoxFlat = card_node.get_theme_stylebox("panel")
		var slot_node: PanelContainer = slot_nodes[slot_idx]
		var slot_style: StyleBoxFlat = slot_node.get_theme_stylebox("panel")

		# Show year label below the card.
		var year_label: Label = slot_node.get_node("YearLabel")
		year_label.text = str(events[event_index]["year"])
		year_label.visible = true

		if event_index == expected_index:
			# Correct placement.
			correct_count += 1
			card_style.border_color = CORRECT_COLOR
			card_style.border_width_left = 3
			card_style.border_width_right = 3
			card_style.border_width_top = 3
			card_style.border_width_bottom = 3
			slot_style.border_color = CORRECT_COLOR
		else:
			# Wrong placement.
			card_style.border_color = WRONG_COLOR
			card_style.border_width_left = 3
			card_style.border_width_right = 3
			card_style.border_width_top = 3
			card_style.border_width_bottom = 3
			slot_style.border_color = WRONG_COLOR

		# Disable interaction.
		card_node.mouse_filter = Control.MOUSE_FILTER_IGNORE

	_show_results()


func _show_results() -> void:
	var total := events.size()
	var pct := float(correct_count) / float(total) * 100.0
	var stars := 0
	if correct_count == total:
		stars = 3
	elif pct >= 80.0:
		stars = 2
	elif pct >= 50.0:
		stars = 1

	_update_feedback(str(correct_count) + "/" + str(total) + " correct!")

	# Show stars.
	for child in star_bar.get_children():
		child.queue_free()

	for i in range(3):
		var star := Label.new()
		if i < stars:
			star.text = "★"
			star.add_theme_color_override("font_color", STAR_ON_COLOR)
		else:
			star.text = "☆"
			star.add_theme_color_override("font_color", STAR_OFF_COLOR)
		star.add_theme_font_size_override("font_size", 28)
		star_bar.add_child(star)

	check_btn.visible = false
	play_again_btn.visible = true


# ── Helpers ──────────────────────────────────────────────────────────────────
func _update_feedback(msg: String) -> void:
	feedback_label.text = msg


func _restart() -> void:
	get_tree().reload_current_scene()
