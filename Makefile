cleanup:
	find ./ -name '*~' -exec rm {} \;
	find ./ -name '#*' -exec rm {} \;
	find ./ -name '*.bak' -exec rm {} \;
	find ./ -name '*.pyc' -exec rm {} \;