extends RefCounted

# Pure game state so the same gameplay is exercised by the headless test and
# the rendered scene. Coordinates are in the fixed 960 x 540 logical viewport.

const FIELD_SIZE := Vector2(960.0, 540.0)
const PADDLE_SIZE := Vector2(22.0, 112.0)
const BALL_RADIUS := 11.0
const PADDLE_MARGIN := 42.0
const PLAYER_X := PADDLE_MARGIN
const AI_X := FIELD_SIZE.x - PADDLE_MARGIN
const PLAYER_SPEED := 520.0
const AI_SPEED := 430.0
const START_BALL_SPEED := 420.0
const MAX_BALL_SPEED := 880.0

var player_y := FIELD_SIZE.y * 0.5
var ai_y := FIELD_SIZE.y * 0.5
var ball_position := FIELD_SIZE * 0.5
var ball_velocity := Vector2(START_BALL_SPEED, 105.0)
var player_score := 0
var ai_score := 0
var rally_hits := 0
var last_event := "round_started"
var next_serve_direction := 1.0


func _init() -> void:
	reset_round(1.0)


func reset_round(direction: float = 0.0) -> void:
	if is_zero_approx(direction):
		direction = next_serve_direction
	next_serve_direction = -signf(direction)
	ball_position = FIELD_SIZE * 0.5
	ball_velocity = Vector2(START_BALL_SPEED * signf(direction), 105.0 * next_serve_direction)
	last_event = "round_started"


func step(delta: float, player_axis: float = 0.0) -> void:
	# A capped step keeps the simulation stable when a mobile device resumes.
	delta = clampf(delta, 0.0, 0.05)
	player_y = clampf(player_y + player_axis * PLAYER_SPEED * delta, _paddle_half_height(), FIELD_SIZE.y - _paddle_half_height())
	_move_ai(delta)
	ball_position += ball_velocity * delta

	if ball_position.y - BALL_RADIUS <= 0.0:
		ball_position.y = BALL_RADIUS
		ball_velocity.y = absf(ball_velocity.y)
		last_event = "wall_bounce"
	elif ball_position.y + BALL_RADIUS >= FIELD_SIZE.y:
		ball_position.y = FIELD_SIZE.y - BALL_RADIUS
		ball_velocity.y = -absf(ball_velocity.y)
		last_event = "wall_bounce"

	if ball_velocity.x < 0.0 and _hits_paddle(PLAYER_X, player_y):
		_bounce_from_paddle(PLAYER_X, player_y, 1.0)
	elif ball_velocity.x > 0.0 and _hits_paddle(AI_X, ai_y):
		_bounce_from_paddle(AI_X, ai_y, -1.0)

	if ball_position.x < -BALL_RADIUS:
		ai_score += 1
		last_event = "ai_scored"
		reset_round(-1.0)
	elif ball_position.x > FIELD_SIZE.x + BALL_RADIUS:
		player_score += 1
		last_event = "player_scored"
		reset_round(1.0)


func snapshot() -> Dictionary:
	return {
		"player_score": player_score,
		"ai_score": ai_score,
		"rally_hits": rally_hits,
		"ball_position": ball_position,
		"ball_velocity": ball_velocity,
		"last_event": last_event,
	}


func _move_ai(delta: float) -> void:
	# The opponent follows the projected ball only while it is approaching;
	# otherwise it recenters, leaving enough room for a human to score.
	var target_y := FIELD_SIZE.y * 0.5
	if ball_velocity.x > 0.0:
		target_y = ball_position.y
	var distance := target_y - ai_y
	ai_y += clampf(distance, -AI_SPEED * delta, AI_SPEED * delta)
	ai_y = clampf(ai_y, _paddle_half_height(), FIELD_SIZE.y - _paddle_half_height())


func _hits_paddle(paddle_x: float, paddle_y: float) -> bool:
	var horizontal_overlap := absf(ball_position.x - paddle_x) <= PADDLE_SIZE.x * 0.5 + BALL_RADIUS
	var vertical_overlap := absf(ball_position.y - paddle_y) <= _paddle_half_height() + BALL_RADIUS
	return horizontal_overlap and vertical_overlap


func _bounce_from_paddle(paddle_x: float, paddle_y: float, direction: float) -> void:
	var offset := clampf((ball_position.y - paddle_y) / _paddle_half_height(), -1.0, 1.0)
	var speed := minf(ball_velocity.length() + 32.0, MAX_BALL_SPEED)
	var rebound := Vector2(direction, offset * 0.78).normalized() * speed
	ball_velocity = rebound
	ball_position.x = paddle_x + direction * (PADDLE_SIZE.x * 0.5 + BALL_RADIUS + 0.5)
	rally_hits += 1
	last_event = "paddle_hit"


func _paddle_half_height() -> float:
	return PADDLE_SIZE.y * 0.5
