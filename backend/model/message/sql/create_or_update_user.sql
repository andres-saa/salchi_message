INSERT INTO messaging.user_message_contact(
	name, wa_user_id)
	VALUES (  %s, %s) returning id, wa_user_id;