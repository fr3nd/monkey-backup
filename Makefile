SCRIPTS := `python -c "import setup; print setup.scripts" | sed "s/[\[\',]//g" | sed "s/\]//g"`
AUTHOR := `python -c "import MonkeyBackup; print MonkeyBackup.__author__" `
EMAIL := `python -c "import MonkeyBackup; print MonkeyBackup.__email__" `
URL := `python -c "import MonkeyBackup; print MonkeyBackup.__url__" `

build: doc
	python setup.py build
	
clean:
	python setup.py clean
	for SCRIPT in ${SCRIPTS}; do rm -f $$SCRIPT.1.gz; done
	rm -rf build dist *.pyc MANIFEST
	rm -f help2man.txt 

install: build
	python setup.py install
	
rpm: build
	python setup.py bdist_rpm

bdist: build
	python setup.py bdist
	
sdist: doc
	python setup.py sdist
	
dist: sdist bdist

doc:
	python -c "import MonkeyBackup; print MonkeyBackup.__name__, MonkeyBackup.__version__; print; print MonkeyBackup.__doc__" > README
	@echo -ne "\nCOMMANDS\n" >> README
	#for SCRIPT in ${SCRIPTS}; do echo -ne "\t$$SCRIPT\t" >> README ; python -c "import MonkeyBackup; print MonkeyBackup.$$SCRIPT.__doc__" >> README ; done
	@echo -ne "\nAUTHOR\n" >> README
	@echo -e "\t${AUTHOR} - ${EMAIL}" >> README
	@echo -e "\t${URL}" >> README
	@echo >> README
	python -c "import MonkeyBackup; print; print \"Licensed under \" + MonkeyBackup.__license__ " >> README
	@echo >> README
	
	#@echo -e "[AUTHOR]\nWritten by ${AUTHOR} - ${EMAIL}\n[SEE ALSO]\n${URL}" > help2man.txt
	#for SCRIPT in ${SCRIPTS}; do  help2man -I help2man.txt -N ./$$SCRIPT | gzip > $$SCRIPT.1.gz; done
