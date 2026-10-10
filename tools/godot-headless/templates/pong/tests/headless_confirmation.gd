extends SceneTree

const ArenaPongSimulation = preload("res://scripts/pong_simulation.gd")
const PASS_MARKER := "PONG_CONFIRMATION_PASS"

var failures: Array[String] = []


func _init() -> void:
	var simulation := ArenaPongSimulation.new()
	_expect(simulation.player_score == 0 and simulation.ai_score == 0, "new match starts at zero-zero")

	# A left-moving ball contacting the human paddle must rebound right.
	simulation.player_y = ArenaPongSimulation.FIELD_SIZE.y * 0.5
	simulation.ball_position = Vector2(
		ArenaPongSimulation.PLAYER_X + ArenaPongSimulation.PADDLE_SIZE.x * 0.5 + ArenaPongSimulation.BALL_RADIUS + 2.0,
		simulation.player_y
	)
	simulation.ball_velocity = Vector2(-ArenaPongSimulation.START_BALL_SPEED, 0.0)
	simulation.step(1.0 / 60.0, 0.0)
	_expect(simulation.ball_velocity.x > 0.0, "human paddle collision reverses the ball")
	_expect(simulation.rally_hits == 1, "paddle collision increments rally count")

	# The computer moves toward an approaching ball.
	var ai_before := simulation.ai_y
	simulation.ball_position = Vector2(ArenaPongSimulation.FIELD_SIZE.x * 0.75, 96.0)
	simulation.ball_velocity = Vector2(150.0, 0.0)
	simulation.step(0.05, 0.0)
	_expect(simulation.ai_y < ai_before, "computer opponent tracks an approaching ball")

	# A missed ball awards a point and starts another round without errors.
	var ai_score_before := simulation.ai_score
	simulation.ball_position = Vector2(-ArenaPongSimulation.BALL_RADIUS - 2.0, simulation.player_y)
	simulation.ball_velocity = Vector2(-ArenaPongSimulation.START_BALL_SPEED, 0.0)
	simulation.step(1.0 / 60.0, 0.0)
	_expect(simulation.ai_score == ai_score_before + 1, "missed human paddle awards the computer a point")
	_expect(simulation.ball_position == ArenaPongSimulation.FIELD_SIZE * 0.5, "scoring resets the ball to center")

	# Run a short deterministic rally with bounded state to exercise the loop.
	for frame in range(360):
		var player_axis := sin(float(frame) * 0.17)
		simulation.step(1.0 / 60.0, player_axis)
	_expect(simulation.player_y >= ArenaPongSimulation.PADDLE_SIZE.y * 0.5, "human paddle stays inside the court")
	_expect(simulation.player_y <= ArenaPongSimulation.FIELD_SIZE.y - ArenaPongSimulation.PADDLE_SIZE.y * 0.5, "human paddle remains below the upper bound")
	_expect(simulation.ai_y >= ArenaPongSimulation.PADDLE_SIZE.y * 0.5, "computer paddle stays inside the court")
	_expect(simulation.ai_y <= ArenaPongSimulation.FIELD_SIZE.y - ArenaPongSimulation.PADDLE_SIZE.y * 0.5, "computer paddle remains below the upper bound")

	if failures.is_empty():
		print(PASS_MARKER)
		print(JSON.stringify(simulation.snapshot()))
		quit(0)
	else:
		for failure in failures:
			printerr("PONG_CONFIRMATION_FAIL: ", failure)
		quit(1)


func _expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
