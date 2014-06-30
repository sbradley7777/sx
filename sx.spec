%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Tool to extract reports and run plug-ins against those extracted reports
Name: sx
Version: 2.17
Release: 2%{?dist}
URL: https://fedorahosted.org/sx
Source0: %{name}-%{version}.tar.gz
License: GPLv2
Group: Applications/Archiving
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
BuildRequires: python-devel >= 2.6.5 python-setuptools
Requires: python >= 2.6.5

%description
sxconsole is a tool used to extract various report types and then
analyze those extracted reports with plug-ins. The tool also provides
an archiving structure so that all the compressed and extracted
reports are saved to a directory. This tool was developed for
sysreport/sosreports but has been expanded to include any report that
has a class defined.

%prep
%setup -q

%build
%{__python} setup.py build

%install
%{__rm} -rf ${RPM_BUILD_ROOT}
%{__python}  setup.py install --optimize 1 --root=${RPM_BUILD_ROOT}

%clean
%{__rm} -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
%doc LICENSE AUTHORS PKG-INFO CHANGELOG
%doc doc/*
%{_bindir}/sxconsole
%{python_sitelib}/*


%changelog
* Fri Dec 02 2011 Shane Bradley <sbradley@redhat.com>- 2.06-15
- Moving the changelog entries that are not related to spec file modification into a seperate file called CHANGELOG.
- Removed python-pycurl dependencey and now error will be printed if that library is required.
* Tue Nov 22 2011 Shane Bradley <sbradley@redhat.com>- 2.06-12
- Removed scsierrors.py, yakuake.py, clusterhaarchreview.py plugins. They will likely go into supplement package.
* Tue Nov 22 2011 Shane Bradley <sbradley@redhat.com>- 2.06-11
- Removed python-libxml2 and moved XML code to elementtree which is native, so that libxml2 is not longer needed as dependency.
* Mon Sep 13 2010 Shane Bradley <sbradley@redhat.com>- 2.03-8
- Updated sx.spec and build procedures to be compliant with fedoraproject.org.
* Thu Aug 26 2010 Shane Bradley <sbradley@redhat.com>- 2.03-7
- Changed LICENSE to GPLv2
- Cleaned up the build process
* Wed Dec 17 2008 Shane Bradley <sbradley@redhat.com>- 1.01-1
- First release of new version of sx with pyqt4 gui support.
