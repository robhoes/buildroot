Name:           ocaml-qmp
Version:        0.9.0
Release:        0
Summary:        Pure OCaml implementation of the Qemu Message Protocol (QMP)
License:        LGPL2.1 + OCaml linking exception
Group:          Development/Other
URL:            http://github.com/xen-org/ocaml-qmp
Source0:        ocaml-qmp-0.9.0.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}
BuildRequires:  ocaml ocaml-findlib
Requires:       ocaml ocaml-findlib

%description
An implementation of the Qemu Message Protocol (QMP) that allows
an application to command, and receive events from, a running qemu
process.

%package        devel
Summary:        Development files for %{name}
Group:          Development/Other
Requires:       %{name} = %{version}-%{release}

%description    devel
The %{name}-devel package contains libraries and signature files for
developing applications that use %{name}.

%prep
%setup -q -n ocaml-qmp-%{version}

%build
if [ -x ./configure ]; then
  ./configure
fi
make

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/%{_libdir}/ocaml
make install DESTDIR=%{buildroot}/%{_libdir}/ocaml

%clean
rm -rf %{buildroot}

%files devel
%defattr(-,root,root)
%doc ChangeLog README.md LICENSE

%{_libdir}/ocaml/qmp/*

%changelog
* Wed May 29 2013 David Scott <dave.scott@eu.citrix.com>
- Initial package
