Name:		fedora-third-party
Version:	0.3
Release:	1%{dist}
Summary:	Tool for handling third-party RPM and Flatpak repositories in Fedora

License:	MIT
URL:		https://pagure.io/fedora-third-party
Source0:	fedora-third-party-%{version}.tar.gz

BuildArch:	noarch

BuildRequires:  systemd
BuildRequires:	polkit
BuildRequires:	python3-click
BuildRequires:	python3-devel
BuildRequires:	python3-pytest
BuildRequires:	python3-setuptools
BuildRequires:  golang-github-cpuguy83-md2man

# For 'dnf config-manager'
Requires: dnf-plugins-core
Requires: python3-click

%description
fedora-third-party is a tool for handling third-party RPM and Flatpak repositories in Fedora.
It is used to handle the user changing their opt-in status for these repositories, and
enables/disables RPM repositories and adds/removes Flatpak repositories as necessary.


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
* Wed Aug 11 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.3-1
- Add --config-only options to the enable/disable subcommands
- Allow detecting whether the config has been explicitly set, or whether no
  decision has been made yet.

* Tue Aug 10 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.2-1
- Fix spec file, add polkit configuration and a --list subcommand

* Fri Jul 30 2021 Owen W. Taylor <otaylor@fishsoup.net> - 0.1-1
- Initial version
