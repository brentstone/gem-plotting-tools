#
# Makefile for gemplotting package
#

BUILD_HOME := $(shell dirname `pwd`)

Project      := gem-plotting-tools
ShortProject := gemplotting
Namespace    := gempython
Package      := gem-plotting-tools
ShortPackage := gemplotting
LongPackage  := gemplotting
PackageName  := $(Namespace)_$(ShortPackage)
PackageDir   := pkg/$(Namespace)/$(ShortPackage)

# Explicitly define the modules that are being exported (for PEP420 compliance)
PythonModules = ["$(Namespace).$(ShortPackage)", \
                 "$(Namespace).$(ShortPackage).fitting", \
                 "$(Namespace).$(ShortPackage).macros", \
                 "$(Namespace).$(ShortPackage).mapping" \
]
$(info PythonModules=${PythonModules})

GEMPLOTTING_VER_MAJOR=1
GEMPLOTTING_VER_MINOR=0
GEMPLOTTING_VER_PATCH=1

include $(BUILD_HOME)/$(Project)/config/mfCommonDefs.mk
include $(BUILD_HOME)/$(Project)/config/mfPythonDefs.mk

# include $(BUILD_HOME)/$(Project)/config/mfDefs.mk

include $(BUILD_HOME)/$(Project)/config/mfPythonRPM.mk

default:
	$(MakeDir) $(PackageDir)
	@cp -rfp macros fitting mapping $(PackageDir)
	@echo "__path__ = __import__('pkgutil').extend_path(__path__, __name__)" > pkg/$(Namespace)/__init__.py
	@cp -rfp __init__.py $(PackageDir)

# need to ensure that the python only stuff is packaged into RPMs
.PHONY: clean preprpm
_rpmprep: preprpm
preprpm: default
	@cp -rfp requirements.txt README.md CHANGELOG.md LICENSE $(PackageDir)
	@cp -rfp requirements.txt README.md CHANGELOG.md pkg
	$(MakeDir) $(PackageDir)/bin
	@cp -rfp ana*.py $(PackageDir)/bin

clean:
	@rm -rf $(PackageDir)/macros
	@rm -rf $(PackageDir)/fitting
	@rm -rf $(PackageDir)/mapping
	@rm -rf $(PackageDir)/bin
	@rm -f  $(PackageDir)/LICENSE
	@rm -f  $(PackageDir)/MANIFEST.in
	@rm -f  $(PackageDir)/requirements.txt
	@rm -f  $(PackageDir)/README.md
	@rm -f  $(PackageDir)/CHANGELOG.md
	@rm -f  $(PackageDir)/__init__.py
	@rm -f  pkg/$(Namespace)/__init__.py
	@rm -f  pkg/README.md
	@rm -f  pkg/CHANGELOG.md
	@rm -f  pkg/requirements.txt

print-env:
	@echo BUILD_HOME     $(BUILD_HOME)
	@echo GIT_VERSION    $(GIT_VERSION)
	@echo PYTHON_VERSION $(PYTHON_VERSION)
	@echo GEMDEVELOPER   $(GEMDEVELOPER)
