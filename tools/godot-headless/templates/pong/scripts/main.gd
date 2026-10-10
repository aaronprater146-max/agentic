extends Node2D

const ArenaPongSimulation = preload("res://scripts/pong_simulation.gd")

var simulation := ArenaPongSimulation.new()
var touch_target_y := -1.0

const BACKGROUND := Color("07111e")
const COURT := Color("17304a")
const PLAYER_COLOR := Color("56d6ff")
const AI_COLOR := Color("ff7d8a")
const BALL_COLOR := Color("fff2b2")
const TEXT_COLOR := Color("dcecff")


func _ready() -> void:
	queue_redraw()


func _process(delta: float) -> void:
	var player_axis := _keyboard_axis()
	if touch_target_y >= 0.0:
		player_axis = clampf((touch_target_y - simulation.player_y) / 48.0, -1.0, 1.0)
	simulation.step(delta, player_axis)
	queue_redraw()


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch and event.pressed:
		touch_target_y = event.position.y
	elif event is InputEventScreenDrag:
		touch_target_y = event.position.y
	elif event is InputEventScreenTouch and not event.pressed:
		touch_target_y = -1.0


func _keyboard_axis() -> float:
	var axis := 0.0
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		axis -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		axis += 1.0
	return axis


func _draw() -> void:
	var field := Rect2(Vector2.ZERO, ArenaPongSimulation.FIELD_SIZE)
	draw_rect(field, BACKGROUND)
	draw_rect(field.grow(-18.0), COURT, false, 2.0)
	for y in range(26, int(ArenaPongSimulation.FIELD_SIZE.y - 20.0), 34):
		draw_rect(Rect2(ArenaPongSimulation.FIELD_SIZE.x * 0.5 - 2.0, y, 4.0, 18.0), Color("31506e"))

	_draw_paddle(ArenaPongSimulation.PLAYER_X, simulation.player_y, PLAYER_COLOR)
	_draw_paddle(ArenaPongSimulation.AI_X, simulation.ai_y, AI_COLOR)
	draw_circle(simulation.ball_position, ArenaPongSimulation.BALL_RADIUS, BALL_COLOR)

	var font := ThemeDB.fallback_font
	draw_string(font, Vector2(340.0, 72.0), str(simulation.player_score), HORIZONTAL_ALIGNMENT_CENTER, 90.0, 54, TEXT_COLOR)
	draw_string(font, Vector2(530.0, 72.0), str(simulation.ai_score), HORIZONTAL_ALIGNMENT_CENTER, 90.0, 54, TEXT_COLOR)
	draw_string(font, Vector2(52.0, 505.0), "W/S or ↑/↓ • touch and drag on mobile", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 18, Color("a8bfd7"))
	draw_string(font, Vector2(660.0, 505.0), "First to your best rally", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 18, Color("a8bfd7"))


func _draw_paddle(x: float, y: float, color: Color) -> void:
	var size := ArenaPongSimulation.PADDLE_SIZE
	var rectangle := Rect2(Vector2(x - size.x * 0.5, y - size.y * 0.5), size)
	draw_rect(rectangle, color)
	draw_rect(rectangle.grow(2.0), Color(color.r, color.g, color.b, 0.35), false, 2.0)
