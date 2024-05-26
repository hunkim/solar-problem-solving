VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip3
STREAMLIT = $(VENV)/bin/streamlit

include .env
export

# Need to use python 3.9 for aws lambda
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt


app: $(VENV)/bin/activate
	$(STREAMLIT) run app.py

codeapp: $(VENV)/bin/activate
	$(STREAMLIT) run code2imgapp.py

code2img: $(VENV)/bin/activate
	$(PYTHON) code2img.py

clean:
	rm -rf __pycache__
	rm -rf $(VENV)