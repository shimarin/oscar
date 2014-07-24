all: oscar.tar

clean:
	rm -f `find . -name '*.pyc' -o -name '*~'`

compile:
	python2.7 -m compileall -q .

lib/web/static/js/oscar.min.js: lib/web/static/js/oscar.js
	PYTHONPATH=lib python -c 'import sys,jsmin;print jsmin.jsmin(open(sys.argv[1]).read())' $< > $@

oscar.tar: compile lib/web/static/js/oscar.min.js
	tar cvf $@ bin/oscar bin/oscar.wsgi lib --exclude='*.py' --exclude='*~' --exclude='lib/web/static/js/test' --exclude='lib/slimit' --exclude='oscar.js'

install: all
	mkdir -p /opt/oscar
	tar xvf oscar.tar -C /opt/oscar
	chown -R oscar /opt/oscar

