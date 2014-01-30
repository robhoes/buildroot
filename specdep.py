#!/usr/bin/python

# see http://docs.fedoraproject.org/en-US/Fedora_Draft_Documentation/0.1/html/RPM_Guide/ch16s04.html

import sys
import argparse
import os
import platform
import urlparse
import pkg

from scripts.lib import mappkgname


def build_type():
    debian_like = ["ubuntu", "debian"]
    rhel_like = ["fedora", "redhat", "centos"]

    dist = platform.linux_distribution(full_distribution_name=False)[0].lower()
    assert dist in debian_like + rhel_like

    if dist in debian_like:
        return "deb"
    elif dist in rhel_like:
        return "rpm"


def map_package_name(name):
    if build_type() == "rpm":
        return [name]
    else:
        return mappkgname.map_package(name)


# Rules to build SRPM from SPEC
def build_srpm_from_spec(spec):
    srpmpath = spec.source_package_path()
    print '%s: %s %s' % (srpmpath, spec.specpath(),
                         " ".join(spec.source_paths()))

    if build_type() == "rpm":
        print '\t@echo [RPMBUILD] $@'
        print '\t@rpmbuild --quiet --define "_topdir ." --define "%%dist %s" -bs $<' % pkg.CHROOT_DIST
    else:
        print '\t@echo [MAKEDEB] $@'
        print '\tscripts/deb/makedeb.py $<'


# Rules to download sources

# Assumes each RPM only needs one download - we have some multi-source
# packages but in all cases the additional sources are patches provided
# in the Git repository
def download_rpm_sources(spec):
    for (url, path) in zip(spec.source_urls(), spec.source_paths()):
        source = urlparse.urlparse(url)

        # Source comes from a remote HTTP server
        if source.scheme in ["http", "https"]:
            print '%s: %s' % (path, spec.specpath())
            print '\t@echo [CURL] $@'
            print '\t@curl --silent --show-error -L -o $@ %s' % url

        # Source comes from a local file or directory
        if source.scheme == "file":
            print '%s: %s $(shell find %s)' % (
                path, spec.specpath(), source.path)

            # Assume that the directory name is already what's expected by the
            # spec file, and prefix it with the version number in the tarball
            print '\t@echo [GIT] $@'
            dirname = "%s-%s" % (os.path.basename(source.path), spec.version())
            print '\t@git --git-dir=%s/.git '\
                'archive --prefix %s/ -o $@ HEAD' % (source.path, dirname)


# Rules to build RPMS from SRPMS (uses information from the SPECs to
# get packages)
def build_rpm_from_srpm(spec):
    # This doesn't generate the right Makefile fragment for a multi-target
    # rule - we may end up building too often, or not rebuilding correctly
    # on a partial build
    rpm_paths = spec.binary_package_paths()
    srpm_path = spec.source_package_path()
    for rpm_path in rpm_paths:
        rpm_outdir = os.path.dirname(rpm_path)
        print '%s: %s' % (rpm_path, srpm_path)
        if build_type() == "rpm":
            print '\t@echo [MOCK] $@'
            print '\t@mock --configdir=mock --quiet -r xenserver '\
                '--resultdir="%s" $<' % rpm_outdir
            print '\t@echo [CREATEREPO] $@'
            print '\t@createrepo --quiet --update %s' % pkg.RPMDIR

        else:
            print '\t@echo [COWBUILDER] $@'
            print '\tsudo cowbuilder --build '\
                '--configfile pbuilder/pbuilderrc-raring-amd64 '\
                '--buildresult %s $<' % rpm_outdir


def package_to_rpm_map(specs):
    provides_to_rpm = {}
    for spec in specs:
        for provided in spec.provides():
            for rpmpath in spec.binary_package_paths():
                provides_to_rpm[provided] = rpmpath
    return provides_to_rpm


def buildrequires_for_rpm(spec, provides_to_rpm):
    for rpmpath in spec.binary_package_paths():
        for buildreq in spec.buildrequires():
            # Some buildrequires come from the system repository
            if provides_to_rpm.has_key(buildreq):
                buildreqrpm = provides_to_rpm[buildreq]
                print "%s: %s" % (rpmpath, buildreqrpm)


def parse_cmdline():
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description=
        "Generate Makefile dependencies from RPM Spec files")
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument("-i", "--ignore", metavar="PKG", action="append",
                        default=[], help="package name to ignore")
    return parser.parse_args()


def main():
    args = parse_cmdline()
    spec_paths = args.specs
    ignore_list = args.ignore
    specs = {}

    for spec_path in spec_paths:
        spec = pkg.Spec(spec_path)
        pkg_name = spec.name()
        if pkg_name in ignore_list:
            continue
        if os.path.splitext(os.path.basename(spec_path))[0] != pkg_name:
            sys.stderr.write(
                "error: spec file name '%s' does not match package name '%s'\n" %
                (spec_path, pkg_name))
            sys.exit(1)

        specs[os.path.basename(spec_path)] = spec

    provides_to_rpm = package_to_rpm_map(specs.values())

    print "all: rpms"

    for spec in specs.itervalues():
        build_srpm_from_spec(spec)
        download_rpm_sources(spec)
        build_rpm_from_srpm(spec)
        buildrequires_for_rpm(spec, provides_to_rpm)
        print ""

    # Generate targets to build all srpms and all rpms
    all_rpms = []
    all_srpms = []
    for spec in specs.itervalues():
        rpm_paths = spec.binary_package_paths()
        all_rpms += rpm_paths
        all_srpms.append(spec.source_package_path())
        print "%s: %s" % (spec.name(), " ".join(rpm_paths))
    print ""

    print "rpms: " + " \\\n\t".join(all_rpms)
    print ""
    print "srpms: " + " \\\n\t".join(all_srpms)
    print ""
    print "install: all"
    print "\t. scripts/%s/install.sh" % build_type()


if __name__ == "__main__":
    main()
