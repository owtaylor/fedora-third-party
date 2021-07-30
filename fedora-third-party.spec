Name:		fedora-third-party
Version:	0.1
Release:	1%{?dist}
Summary:	Tool for handling third-party RPM and Flatpak repositories in Fedora

License:	MIT
URL:		https://pagure.io/fedora-third-party
Source0:	https://releases.pagure.org/fedora-third-party/fedora-third-party-%{version}.tar.gz

BuildArch:	noarch

BuildRequires:	python3-setuptools

Requires: python3-click

%description
fedora-third-party is a tool for handling third-party RPM and Flatpak repositories in Fedora.
It is used to handle the user changing their opt-in status for these repositories, and
enables/disables RPM repositories and adds/removes Flatpak repositories as necessary.


%prep
%autosetup -p1


%build
%py3_build


%check
%pytest


%install
%py3_install


%files
%license LICENSE
%doc README.md
%{_bindir}/fedora-third-party
%{python3_sitelib}/*


%changelog
* Tue Jul 30 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.1-1
- Initial version
