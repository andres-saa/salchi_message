INSERT INTO messaging.message(
	wa_id, user_id, content, context_message_id, current_status_id, employer_id, wa_timestamp, restaurant_id)
	VALUES (%s, %s, %s, %s, %s, %s, %s, %s);