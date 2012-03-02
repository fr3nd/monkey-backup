%define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")

Name        : monkey-backup
Version     : 0.2.2
Release     : 1

License     : GPL
Summary     : Multithreaded modular backup script
Group       : Applications/Archiving

Url         : http://www.fr3nd.net/projects/monkey-backup/
Vendor      : Carles Amigo <fr3nd@fr3nd.net>

BuildRoot   : %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Source0     : %{name}-%{version}.tar.gz
Source1     : monkey-backup.ini
Source2     : exclude.txt

Prefix      : %{_prefix}
BuildArch   : noarch

Requires    : python
Requires    : python-paramiko
#BuildRequires: help2man
BuildRequires: python

%description
Modular backup script which allows to execute remote backups to multiple
servers at the same time

%prep
rm -rf %{buildroot}

%setup

%build
CFLAGS="%{optflags}" %{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install --skip-build --root="%{buildroot}" --prefix="%{_prefix}"
%{__mkdir} -p %{buildroot}/backup/monkey-backup
%{__mkdir} -p %{buildroot}/var/log/monkey-backup
%{__mkdir} -p %{buildroot}%{_sysconfdir}/monkey-backup
%{__install} %{SOURCE1} %{buildroot}%{_sysconfdir}/monkey-backup
%{__install} %{SOURCE2} %{buildroot}%{_sysconfdir}/monkey-backup

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-, root, root, 0755)
/usr/bin/monkey-backup
%{python_sitelib}/MonkeyBackup.py
%{python_sitelib}/*.pyc
%config %{_sysconfdir}/monkey-backup/monkey-backup.ini
%config %{_sysconfdir}/monkey-backup/exclude.txt
%dir /backup/monkey-backup
%dir /var/log/monkey-backup

%changelog
* Tue May 30 2011 Carles Amigo <carles.amigo@softonic.com> 0.2.2-1
- New version

* Thu Sep 30 2010 Carles Amigo <carles.amigo@softonic.com>
- Initial RPM build
