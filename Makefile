
req:
	pip install -r requirements.txt

build:
	python setup.py py2app

all: req build

