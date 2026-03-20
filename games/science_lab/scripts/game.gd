extends Control

# ---------------------------------------------------------------------------
# Science Lab  --  drag-and-drop experiment simulation
# ---------------------------------------------------------------------------

# --- node refs (unique names) ---
@onready var experiment_name_label: Label       = %ExperimentNameLabel
@onready var progress_label: Label               = %ProgressLabel
@onready var instruction_label: Label            = %InstructionLabel
@onready var materials_panel: VBoxContainer       = %MaterialsPanel
@onready var experiment_zone: Control            = %ExperimentZone
@onready var zone_label: Label                   = %ZoneLabel
@onready var placed_container: VBoxContainer     = %PlacedContainer
@onready var run_button: Button                  = %RunButton
@onready var next_button: Button                 = %NextButton
@onready var result_label: Label                 = %ResultLabel
@onready var stars_container: HBoxContainer      = %StarsContainer

# --- palette ---
const COL_BG           := Color("e8f5e9")
const COL_ZONE_BG      := Color("f1f8e9")
const COL_ZONE_BORDER  := Color("66bb6a")
const COL_CARD_BG      := Color("ffffff")
const COL_CARD_HOVER   := Color("c8e6c9")
const COL_CORRECT      := Color("4caf50")
const COL_WRONG        := Color("ef5350")
const COL_TEXT_DARK     := Color("263238")
const COL_TEXT_MED      := Color("546e7a")
const COL_ACCENT       := Color("2e7d32")

# --- state ---
var config: Dictionary = {}
var experiments: Array = []
var current_exp_index: int = 0
var placed_materials: Array[String] = []
var wrong_drops: int = 0
var scores: Array[int] = []          # stars per experiment

var dragging_card: PanelContainer = null
var drag_offset: Vector2 = Vector2.ZERO
var drag_original_pos: Vector2 = Vector2.ZERO
var drag_original_parent: Control = null

# -----------------------------------------------------------------------
#  LIFECYCLE
# -----------------------------------------------------------------------
func _ready() -> void:
	_load_config()
	run_button.pressed.connect(_on_run_experiment)
	next_button.pressed.connect(_on_next_experiment)
	_setup_experiment()


func _load_config() -> void:
	var file := FileAccess.open("res://config.json", FileAccess.READ)
	if file == null:
		push_error("Could not open config.json")
		return
	var json := JSON.new()
	var err := json.parse(file.get_as_text())
	file.close()
	if err != OK:
		push_error("JSON parse error: " + json.get_error_message())
		return
	config = json.data
	experiments = config.get("experiments", [])


# -----------------------------------------------------------------------
#  EXPERIMENT SETUP
# -----------------------------------------------------------------------
func _setup_experiment() -> void:
	if current_exp_index >= experiments.size():
		_show_final_score()
		return

	var exp: Dictionary = experiments[current_exp_index]

	# header
	experiment_name_label.text = exp.get("name", "")
	progress_label.text = "%d / %d" % [current_exp_index + 1, experiments.size()]
	instruction_label.text = exp.get("instruction", "")

	# reset state
	placed_materials.clear()
	wrong_drops = 0

	# clear previous material cards
	for child in materials_panel.get_children():
		child.queue_free()

	# clear placed items
	for child in placed_container.get_children():
		child.queue_free()

	# build new cards  (shuffled)
	var mats: Array = exp.get("materials", []).duplicate()
	mats.shuffle()
	for mat_name in mats:
		var card := _create_material_card(mat_name)
		materials_panel.add_child(card)

	# zone label
	zone_label.text = "Drop materials here\nin the correct order"
	zone_label.visible = true

	# buttons / result
	run_button.visible = false
	next_button.visible = false
	result_label.text = ""
	_clear_stars()


func _create_material_card(mat_name: String) -> PanelContainer:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(170, 44)

	# style
	var style := StyleBoxFlat.new()
	style.bg_color = COL_CARD_BG
	style.border_color = COL_ZONE_BORDER
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(8)
	card.add_theme_stylebox_override("panel", style)

	# label
	var lbl := Label.new()
	lbl.text = "  " + mat_name
	lbl.add_theme_color_override("font_color", COL_TEXT_DARK)
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	card.add_child(lbl)

	# store name
	card.set_meta("mat_name", mat_name)

	# interaction
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	card.gui_input.connect(_on_card_gui_input.bind(card))

	return card


# -----------------------------------------------------------------------
#  DRAG & DROP  (manual, works in Godot 4.3 without _get_drag_data)
# -----------------------------------------------------------------------
func _on_card_gui_input(event: InputEvent, card: PanelContainer) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_start_drag(card, mb.global_position)
			else:
				if dragging_card == card:
					_end_drag(mb.global_position)


func _input(event: InputEvent) -> void:
	if dragging_card == null:
		return
	if event is InputEventMouseMotion:
		dragging_card.global_position = event.global_position - drag_offset
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT and not mb.pressed:
			_end_drag(mb.global_position)


func _start_drag(card: PanelContainer, gpos: Vector2) -> void:
	dragging_card = card
	drag_offset = gpos - card.global_position
	drag_original_pos = card.global_position
	drag_original_parent = card.get_parent()

	# re-parent to root so it renders on top
	var gp := card.global_position
	drag_original_parent.remove_child(card)
	add_child(card)
	card.global_position = gp
	card.z_index = 100


func _end_drag(gpos: Vector2) -> void:
	if dragging_card == null:
		return
	var card := dragging_card
	dragging_card = null

	# check if dropped inside zone
	var zone_rect := Rect2(experiment_zone.global_position, experiment_zone.size)
	if zone_rect.has_point(gpos):
		_handle_drop(card)
	else:
		_bounce_back(card)


func _handle_drop(card: PanelContainer) -> void:
	var mat_name: String = card.get_meta("mat_name")
	var exp: Dictionary = experiments[current_exp_index]
	var correct_order: Array = exp.get("correct_order", [])
	var next_index := placed_materials.size()

	if next_index < correct_order.size() and correct_order[next_index] == mat_name:
		# CORRECT
		placed_materials.append(mat_name)
		_place_in_zone(card)
		_flash_card(card, COL_CORRECT)
		if placed_materials.size() >= correct_order.size():
			_all_placed()
	else:
		# WRONG
		wrong_drops += 1
		_flash_card(card, COL_WRONG)
		_bounce_back(card)
		_show_hint("Try again! Check the order.")


func _place_in_zone(card: PanelContainer) -> void:
	# remove from root, add to placed_container
	if card.get_parent():
		card.get_parent().remove_child(card)
	card.z_index = 0
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE

	# green border
	var style := card.get_theme_stylebox("panel").duplicate() as StyleBoxFlat
	style.border_color = COL_CORRECT
	style.bg_color = Color("e8f5e9")
	card.add_theme_stylebox_override("panel", style)

	placed_container.add_child(card)

	# hide hint label when first item placed
	if placed_materials.size() == 1:
		zone_label.visible = false


func _bounce_back(card: PanelContainer) -> void:
	# return card to materials panel
	if card.get_parent():
		card.get_parent().remove_child(card)
	card.z_index = 0
	materials_panel.add_child(card)


func _flash_card(card: PanelContainer, color: Color) -> void:
	var style := card.get_theme_stylebox("panel").duplicate() as StyleBoxFlat
	var orig_bg := style.bg_color
	style.bg_color = color
	card.add_theme_stylebox_override("panel", style)

	var tw := create_tween()
	tw.tween_callback(func():
		var s2 := card.get_theme_stylebox("panel").duplicate() as StyleBoxFlat
		s2.bg_color = orig_bg
		card.add_theme_stylebox_override("panel", s2)
	).set_delay(0.3)


func _show_hint(msg: String) -> void:
	result_label.add_theme_color_override("font_color", COL_WRONG)
	result_label.text = msg
	var tw := create_tween()
	tw.tween_callback(func():
		if result_label.text == msg:
			result_label.text = ""
	).set_delay(1.5)


# -----------------------------------------------------------------------
#  ALL PLACED  --  show Run Experiment button
# -----------------------------------------------------------------------
func _all_placed() -> void:
	run_button.visible = true
	result_label.add_theme_color_override("font_color", COL_ACCENT)
	result_label.text = "All materials placed! Ready to run."


# -----------------------------------------------------------------------
#  RUN EXPERIMENT
# -----------------------------------------------------------------------
func _on_run_experiment() -> void:
	run_button.visible = false
	var exp: Dictionary = experiments[current_exp_index]

	# --- glow / pulse animation on the zone ---
	var zone_bg: ColorRect = null
	for child in experiment_zone.get_children():
		if child is ColorRect:
			zone_bg = child as ColorRect
			break

	if zone_bg:
		var tw := create_tween()
		tw.set_loops(3)
		tw.tween_property(zone_bg, "color", COL_CORRECT.lightened(0.4), 0.25)
		tw.tween_property(zone_bg, "color", COL_ZONE_BG, 0.25)
		await tw.finished

	# show result
	var emoji: String = exp.get("result_emoji", "")
	var result_text: String = exp.get("result", "")
	result_label.add_theme_color_override("font_color", COL_TEXT_DARK)
	result_label.text = emoji + "  " + result_text

	# stars
	var star_count := _calc_stars()
	scores.append(star_count)
	_show_stars(star_count)

	# next button
	if current_exp_index < experiments.size() - 1:
		next_button.text = "Next Experiment  ->"
	else:
		next_button.text = "See Final Score"
	next_button.visible = true


func _calc_stars() -> int:
	if wrong_drops == 0:
		return 3
	elif wrong_drops <= 2:
		return 2
	else:
		return 1


func _show_stars(count: int) -> void:
	_clear_stars()
	for i in range(3):
		var star := Label.new()
		star.add_theme_font_size_override("font_size", 28)
		if i < count:
			star.text = "*"
			star.add_theme_color_override("font_color", Color("ffc107"))
		else:
			star.text = "*"
			star.add_theme_color_override("font_color", Color("cfd8dc"))
		stars_container.add_child(star)


func _clear_stars() -> void:
	for child in stars_container.get_children():
		child.queue_free()


# -----------------------------------------------------------------------
#  NEXT / FINAL
# -----------------------------------------------------------------------
func _on_next_experiment() -> void:
	current_exp_index += 1
	_setup_experiment()


func _show_final_score() -> void:
	# hide normal UI pieces
	instruction_label.text = ""
	for child in materials_panel.get_children():
		child.queue_free()
	for child in placed_container.get_children():
		child.queue_free()
	zone_label.visible = false
	run_button.visible = false
	next_button.visible = false
	_clear_stars()

	experiment_name_label.text = "Experiment Complete!"
	progress_label.text = ""

	var total_stars := 0
	var max_stars := scores.size() * 3
	for s in scores:
		total_stars += s

	var grade_text := ""
	if total_stars == max_stars:
		grade_text = "PERFECT! You're a real scientist!"
	elif total_stars >= max_stars * 0.7:
		grade_text = "Great job! Keep experimenting!"
	else:
		grade_text = "Good try! Practice makes perfect!"

	result_label.add_theme_color_override("font_color", COL_TEXT_DARK)
	result_label.text = grade_text

	# show total stars
	for i in range(max_stars):
		var star := Label.new()
		star.add_theme_font_size_override("font_size", 24)
		if i < total_stars:
			star.text = "*"
			star.add_theme_color_override("font_color", Color("ffc107"))
		else:
			star.text = "*"
			star.add_theme_color_override("font_color", Color("cfd8dc"))
		stars_container.add_child(star)

	# add a restart button
	var restart_btn := Button.new()
	restart_btn.text = "Play Again"
	restart_btn.custom_minimum_size = Vector2(140, 40)

	var restart_style := StyleBoxFlat.new()
	restart_style.bg_color = COL_ACCENT
	restart_style.set_corner_radius_all(8)
	restart_style.set_content_margin_all(8)
	restart_btn.add_theme_stylebox_override("normal", restart_style)
	restart_btn.add_theme_color_override("font_color", Color.WHITE)

	restart_btn.pressed.connect(func():
		current_exp_index = 0
		scores.clear()
		restart_btn.queue_free()
		_setup_experiment()
	)
	stars_container.add_child(restart_btn)
