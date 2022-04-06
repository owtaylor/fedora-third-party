Name:		fedora-third-party
Version:	0.10
Release:	1%{dist}
Summary:	Tool for handling third-party RPM and Flatpak repositories in Fedora

License:	MIT
URL:		https://pagure.io/fedora-third-party
Source0:	fedora-third-party-%{version}.tar.gz

BuildArch:	noarch

BuildRequires:	systemd
BuildRequires:	polkit
BuildRequires:	python3-click
BuildRequires:	python3-devel
BuildRequires:  python3-gobject-base
BuildRequires:	python3-pytest
BuildRequires:	python3-setuptools
BuildRequires:	golang-github-cpuguy83-md2man

Requires: python3-click
Requires: python3-gobject-base

%description
fedora-third-party is a tool for handling third-party RPM and Flatpak
repositories in Fedora.  It is used to handle the user changing their opt-in
status for these repositories, and enables/disables RPM repositories and
adds/removes Flatpak repositories as necessary.


%prep
%autosetup -p1


%build
%py3_build

go-md2man -in doc/%{name}.1.md -out doc/%{name}.1


%check
%pytest


%install
%py3_install

# This script is just for use under pkexec, move it out of bindir to avoid confusion
mkdir -p %{buildroot}%{_prefix}/lib/%{name}
mv %{buildroot}%{_bindir}/fedora-third-party-opt-out %{buildroot}%{_prefix}/lib/%{name}/fedora-third-party-opt-out

mkdir -p %{buildroot}%{_localstatedir}/lib/%{name}
mkdir -p %{buildroot}%{_prefix}/lib/%{name}/conf.d

install -m0644 -D doc/%{name}.1 -t %{buildroot}%{_mandir}/man1
install -m0644 -D systemd/fedora-third-party-refresh.service -t %{buildroot}%{_unitdir}
install -m0644 -D polkit/org.fedoraproject.thirdparty.policy -t %{buildroot}%{_datadir}/polkit-1/actions
install -m0644 -D polkit/org.fedoraproject.thirdparty.rules -t %{buildroot}%{_datadir}/polkit-1/rules.d


%files
%license LICENSE
%doc README.md
%{_bindir}/%{name}
%{_datadir}/polkit-1/actions/*.policy
%{_datadir}/polkit-1/rules.d/*.rules
%{python3_sitelib}/fedora_third_party*
%{_localstatedir}/lib/%{name}
%{_prefix}/lib/%{name}
%{_mandir}/man1/%{name}.1*
%{_unitdir}/*.service


%post
%systemd_post fedora-third-party-refresh.service

%preun
%systemd_preun fedora-third-party-refresh.service

%postun
%systemd_postun_with_restart fedora-third-party-refresh.service

%dnl This enables/adds any newly added repositories/remotes
%transfiletriggerin -- %{_prefix}/lib/%{name}/conf.d
fedora-third-party refresh

%dnl This could potentially be used to remove Flatpak repositories (not currently implemented)
%transfiletriggerpostun -- %{_prefix}/lib/%{name}/conf.d
fedora-third-party refresh || :


%changelog
* Thu Mar 30 2022 Owen W. Taylor <otaylor@fishsoup.net> - 0.10-1
- Fix a problem with parsing Flatpak output
- Improve handling of disabled Flatpak repositories on upgrades from an
  old version of fedora-third-party.
- Gracefully handle failures running 'flatpak' commands

* Thu Mar 30 2022 Owen W. Taylor <otaylor@fishsoup.net> - 0.9-1
- Fix problem where title from .flatpakrepo files was ignored
- Enable/disable Flathub repositories instead of adding/removing them
  (Create disabled when opting out)

* Fri Oct 15 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.8-1
- Drop a chcon call that was making problems for selinux confinement

* Tue Oct 5 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.7-1
- Don't show repositories that are modified to remove the filter in
  the output of `fedora-third-party list.

* Mon Aug 16 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.6-1
- Don't write /var/lib/fedora-third-party/state on refresh if no changes
  Resolves: rhbz#1994830

* Mon Aug 16 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.5-1
- Remove dependency on 'dnf config-manager'
- Make fedora-third-party-refresh.service only run on rpm-ostree systems

* Wed Aug 11 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.4-1
- Add a special 'fedora-third-party-opt-out' script to go from unset => disabled
  without a polkit auth dialog.

* Wed Aug 11 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.3-1
- Add --config-only options to the enable/disable subcommands
- Allow detecting whether the config has been explicitly set, or whether no
  decision has been made yet.

* Tue Aug 10 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.2-1
- Fix spec file, add polkit configuration and a --list subcommand

* Fri Jul 30 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.1-1
- Initial version
