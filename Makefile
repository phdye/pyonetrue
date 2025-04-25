NAME           := pyonetrue
PROJECT        := $${PWD\#\#*/}
# FILES          := {Makefile,${NAME},doc/0.5,src,tests,scripts}
FILES          := {Makefile,src,tests,scripts}

# make test n=1 t="test/*_wh*.py"
NETWORK        := $(or $(NETWORK), $(network), $(N), $(n))
TESTS_TO_RUN   := $(or $(TEST), $(test), ${T}, ${t}, tests)
PYTEST_FLAGS   := 

FLATTEN_ARGS   := $(or $(FLATTEN_ARGS), $(flatten_args), $(f))
SINGLE_ARGS    := $(or $(SINGLE_ARGS), $(single_args), $(s))
SRC_DIRS       := src tests scripts
DOWNLOAD_DIRS  := generated out
ERRORS         := /dn/errors.txt

PYTHON         := python3
PYLINT         := pylint
BLACK          := black
ISORT          := isort

.PHONY: all check test clean layout tar input itest pytest

all: clear-errors check test

ifeq ($(NETWORK),1)
  PYTEST_FLAGS += --run-network
endif

test: clear-errors
	err PYTHONPATH=$$(pwd)/src pytest -s ${PYTEST_FLAGS} ${TESTS_TO_RUN}

mtest: clear-errors
	err -a scripts/run-tests --module pyonetrue --tmp-packages

flatten:
	mkdir -p flat
	rm -f ${PROJECT}
	name=${PROJECT} && \
      PYTHONPATH=$$(pwd)/src scripts/$${name} $${name} --no-cli --output=flat/$${name}.py $(FLATTEN_ARGS)
	touch ${PROJECT} && chmod 0444 ${PROJECT}

single:
	@ set -x && \
      name=${PROJECT} && \
      output=scripts/$${name} && \
      PYTHONPATH=$$(pwd)/src python3 -m $${name} $${name} --output=$${output} $(SINGLE_ARGS) && \
      chmod 0755 $${output}

cx clear-errors:
	rm -f $(ERRORS)

clean:
	@ echo "Cleaning up ..."
	yes | clean
	rm -f env.json vars.json $(ERRORS) .errors.*
	rm -rf build dist ${DOWNLOAD_DIRS}
	find . -name '*.pyc'               -delete
	find . -name '__pycache__'         | xargs rm -rf
	find . -name '.pytest_cache'       | xargs rm -rf
	find . -name '*.egg-info'          | xargs rm -rf

dist-clean: clean
	@ echo "Dist Cleaning up..."
	rm -rf build dist

layout:
	@ stree $$(echo ${FILES} | tr , ' ') | tee doc/layout.txt

check:
	@echo "Running static analysis on: $(SRC_DIRS)"
	@$(PYLINT) $(SRC_DIRS)
	@$(BLACK) --check $(SRC_DIRS)
	@$(ISORT) --check-only $(SRC_DIRS)

tar: clean
	@ ( name=${PROJECT} && cd .. && tar cvfJ /dn/$${name}.tar.xz --exclude="*/__pycache__" $${name}/${FILES} )
	@ ( name=${PROJECT} && tar tf /dn/$${name}.tar.xz > /dn/$${name}.tar.xz.list )

# refresh content w/o bootstrap
tar-in:
	@ name=${PROJECT} && ( tar cvfJ /dn/$${name}.in.tar.xz --exclude="*/__pycache__" ${FILES} )

UNZIP_LOG := /dn/unzip.log

unzip:
	@ unzip -o /dn/${PROJECT}.zip | tee $(UNZIP_LOG)

unzip-list:
	@ unzip -l /dn/${PROJECT}.zip | tee $(UNZIP_LOG)

update:
	@ unzip -o /dn/${PROJECT}.update.zip | tee $(UNZIP_LOG)

update-list ul:
	@ unzip -l /dn/${PROJECT}.update.zip | tee $(UNZIP_LOG)

unzip-lines:
	@ ( echo ; echo "Lines:" ) >> $(UNZIP_LOG)
	@ ( cat $(UNZIP_LOG) ) | sed -e '/Archive:/d;s/^\s*inflating: //g' | xargs wc -l | tee -a $(UNZIP_LOG)
