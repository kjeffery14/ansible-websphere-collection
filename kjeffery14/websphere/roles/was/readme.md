# WAS 9.0.5 Silent Installation

[Installing the product offerings by using response files](https://www.ibm.com/docs/en/was-nd/9.0.5?topic=offerings-installing-product-by-using-response-files)

```bash
./imcl -acceptLicense 
  input /var/temp/install_response_file.xml 
  -secureStorageFile /var/IM/credential.store -masterPasswordFile /var/IM/master_password.txt
  -log /var/temp/install_log.xml 
```

```bash
./imcl install com.ibm.websphere.ND.v90 com.ibm.java.jdk.v8
  -repositories http://www.ibm.com/software/repositorymanager/com.ibm.websphere.ND.v90 
  -installationDirectory /opt/IBM/WebSphere/AppServer
  -sharedResourcesDirectory /opt/IBM/IMShared
  -preferences com.ibm.cic.common.core.preferences.keepFetchedFiles=false,com.ibm.cic.common.core.preferences.preserveDownloadedArtifacts=false
  -secureStorageFile /var/IM/credential.store -masterPasswordFile /var/IM/master_password.txt
  -log installv9.xml
  -acceptLicense
  -showProgress
```

[Storing Credentials for Installation Manager repositories](https://www.ibm.com/docs/en/installation-manager/1.8.5?topic=mode-storing-credentials)

```bash
./imutilsc saveCredential 
  -secureStorageFile storage_file
  -userName user_ID -userPassword user_password
  -url source_repository 
```
