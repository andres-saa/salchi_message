UPDATE messaging.message
	SET  current_status_id=%s
	WHERE  wa_id=%s;