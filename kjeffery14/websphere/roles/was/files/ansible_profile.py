# roles/was/files/ansible_profile.py
# @version v1.05_2023-FEB-03
# @author Kevin Jeffery

import json

def getIdSpec( name, type):
  return '/' + type + ':' + name + '/'

def getNodeScope(nodeName):
  cell = AdminControl.getCell()
  if nodeName is None: return '(cell):{0}'.format(cell)
  return '(cell):{0}:(node):{1}'.format(cell, nodeName)

def createCluster(clusterName, warnings=[]):
  cellName = AdminControl.getCell()
  cellId = AdminConfig.getid(getIdSpec(cellName, 'Cell'))
  clusterId = AdminConfig.getid(getIdSpec(clusterName, 'ServerCluster'))
  if clusterId == '':
    clusterId = AdminConfig.create('ServerCluster', cellId, [['name', clusterName]])
    warnings.append("Created Cluster: {0}".format(clusterId))
    return True, warnings
  else:
    warnings.append("Cluster Exists: {0}".format(clusterId))
  return False, warnings

def createClusterMember(serverName, clusterName, nodeName, warnings=[]):
  serverId = AdminConfig.getid(getIdSpec(serverName, 'Server'))
  if serverId != "":
    warnings.append('Server Exists: {0}'.format(serverId))
    return False, warnings
  clusterId = AdminConfig.getid(getIdSpec(clusterName, 'ServerCluster'))
  nodeId = AdminConfig.getid(getIdSpec(nodeName, 'Node'))
  AdminConfig.createClusterMember(clusterId, nodeId, [['memberName', serverName]])
  warnings.append('Added Server: {0} to {1} {2}'.format(serverName, clusterName, nodeName))
  serverId = AdminConfig.getid(getIdSpec(serverName, 'Server'))
  pmiId = AdminConfig.list('PMIService', serverId)
  AdminConfig.modify(pmiId,  [['enable', 'false']])
  warnings.append("Disable PMI Service: {0}".format(pmiId))
  return True, warnings

def importCACerts (certAlias, certFile, warnings=[]):
  certAlias = certAlias.lower()
  changed = False
  reply, warnings = importCACert('CellDefaultTrustStore', None, certAlias, certFile, warnings)
  changed |= reply
  reply, warnings = importCACert('CellDefaultKeyStore', None, certAlias, certFile, warnings)
  changed |= reply
  nodeIds = AdminConfig.list('Node').split('\n')
  for nodeId in nodeIds:
    nodeName = AdminConfig.showAttribute(nodeId, 'name')
    if nodeName == 'dmgr': continue
    reply, warnings = importCACert('NodeDefaultTrustStore', nodeName, certAlias, certFile, warnings)
    changed |= reply
    reply, warnings = importCACert('NodeDefaultKeyStore', nodeName, certAlias, certFile, warnings)
    changed |= reply
  return changed, warnings

def importCACert (keyStoreName, nodeName, certAlias, certFile, warnings=[]):
  keyStoreScope = getNodeScope(nodeName)
  exists, certList = getSignerCerts(keyStoreName, keyStoreScope)
  if not exists:
    warnings.append('Keystore not found: {0} {1}'.format(keyStoreScope, keyStoreName))
    return False, warnings
  isCert = hasAlias(certList, certAlias)
  if isCert:
    warnings.append('Cert Exists: {0} in {1} {2}'.format(certAlias, keyStoreScope, keyStoreName))
    return False, warnings
  return addCACert(keyStoreName, nodeName, certAlias, certFile, warnings)

def hasAlias(certList, certAlias):
  for item in certList:
    if '[alias {0}]'.format(certAlias) in item:
      return True
  return False

def getSignerCerts(keyStoreName, keyStoreScope):
  params = ['-keyStoreName', keyStoreName, '-keyStoreScope', keyStoreScope ]
  try:
    certList = AdminTask.listSignerCertificates(params).split('\n')
    return True, certList
  except:
    return False, None

def addCACert (keyStoreName, nodeName, certAlias, certFile, warnings=[]):
  keyStoreScope = getNodeScope(nodeName)
  params = ['-keyStoreName', keyStoreName, '-keyStoreScope', keyStoreScope, '-certificateAlias', certAlias, '-certificateFilePath', certFile, '-base64Encoded', 'true']
  try:
    AdminTask.addSignerCertificate(params)
  except:
    warnings.append('Cert failed: {0} in {1} {2}'.format(certAlias, keyStoreScope, keyStoreName))
    return False, warnings
  warnings.append('Cert added: {0} in {1} {2}'.format(certAlias, keyStoreScope, keyStoreName))
  return True, warnings

def importPersonalCert (keyStoreName, nodeName, certAlias, keyFile, keyPwd, keyFileType='PKCS12', warnings=[]):
  keyStoreScope = getNodeScope(nodeName)
  exists, certList = getPersonalCerts(keyStoreName, keyStoreScope)
  if not exists:
    warnings.append('Keystore not found: {0} {1}'.format(keyStoreScope, keyStoreName))
    return False, warnings
  isCert = hasAlias(certList, certAlias)
  if isCert:
    warnings.append('Key Exists: {0} in {1} {2}'.format(certAlias, keyStoreScope, keyStoreName))
    return False, warnings
  return addPersonalCert(keyStoreName, nodeName, certAlias, keyFile, keyPwd, keyFileType=keyFileType, warnings=warnings)

def getPersonalCerts(keyStoreName, keyStoreScope):
  params = ['-keyStoreName', keyStoreName, '-keyStoreScope', keyStoreScope ]
  try:
    certList = AdminTask.listPersonalCertificates(params).split('\n')
    return True, certList
  except:
    return False, None

def addPersonalCert (keyStoreName, nodeName, certAlias, keyFilePath, keyFilePassword, keyFileType='PKCS12', warnings=[]):
  keyStoreScope = getNodeScope(nodeName)
  params = ['-keyStoreName', keyStoreName, '-keyStoreScope', keyStoreScope, '-certificateAlias', certAlias, '-keyFilePath', keyFilePath, '-keyFilePassword', keyFilePassword, '-keyFileType', keyFileType, '-certificateAliasFromKeyFile', certAlias]
  try:
    AdminTask.importCertificate(params)
  except:
    warnings.append('Key failed: {0} in {1} {2}'.format(certAlias, keyStoreScope, keyStoreName))
    return False, warnings
  warnings.append("Key added: {0} ub {1} {2}".format(certAlias, keyStoreScope, keyStoreName))
  return True, warnings

def createUnmanagedNode(nodeName, hostName, nodeOperatingSystem='linux', warnings=[]):
  nodeExists, warnings = hasNode(nodeName, warnings)
  if nodeExists: return True, warnings
  params = ['-nodeName', nodeName, '-hostName', hostName, '-nodeOperatingSystem', nodeOperatingSystem]
  AdminTask.createUnmanagedNode(params)
  return hasNode(nodeName, warnings)

def hasNode(nodeName, warnings=[]):
  nodeList = AdminTask.listNodes().split('\n')
  if nodeName in nodeList: return True, warnings
  return False, warnings

def getSSLConfigCertAlias(sslConfigAlias, nodeName, warnings=[]):
  scopeName = getNodeScope(nodeName)
  params = ['-alias', sslConfigAlias, '-scopeName', scopeName, '-returnAttributes', 'alias,serverKeyAlias,clientKeyAlias']
  try: reply = AdminTask.getSSLConfig(params)
  except:
    warnings.append('Not Found: {0} {1}'.format(scopeName, sslConfigAlias))
    return None, warnings
  return reply, warnings

def setSSLConfig(sslConfigAlias, certAlias, nodeName, warnings=[], sslProtocolList=None):
  sslConfig, warnings = getSSLConfigCertAlias(sslConfigAlias, nodeName, warnings=warnings)
  if sslConfig is None: return False, warnings
  scopeName = getNodeScope(nodeName)
  try:
    params = ['-alias', sslConfigAlias, '-scopeName', scopeName, '-serverKeyAlias', certAlias, '-clientKeyAlias', certAlias]
    if sslProtocolList is None:
      params.append('-sslProtocol')
      params.append('TLSv1.2,TLSv1.3')
    else:
      params.append('-sslProtocol')
      params.append(sslProtocolList)
    AdminTask.modifySSLConfig(params)
    if AdminConfig.hasChanges():
      warnings.append('Modified: {0} in {1} {2}'.format(certAlias, scopeName, sslConfigAlias))
      return True, warnings
    warnings.append('Unchanged: {0} in {1} {2}'.format(certAlias, scopeName, sslConfigAlias))
    return False, warnings
  except:
    warnings.append('Error: {0} {1}'.format(scopeName, sslConfigAlias))
    return False, warnings

def getSSLConfigGroup(nodeName, direction='inbound', warnings=[]):
  scopeName = getNodeScope(nodeName)
  if nodeName is None: nodeName = AdminControl.getCell()
  params = ['-name', nodeName, '-direction', direction, '-scopeName', scopeName]
  try:
    reply = AdminTask.getSSLConfigGroup(params)
  except:
    warnings.append('Not Found: {0} {1}'.format(scopeName, direction))
    return False, None, warnings
  return True, reply, warnings

def setSSLConfigGroup(sslConfigAlias, certAlias, nodeName, warnings=[], direction='inbound'):
  exists, sslConfigGroup, warnings = getSSLConfigGroup(nodeName, direction=direction, warnings=warnings)
  if not exists: return False, warnings
  scopeName = getNodeScope(nodeName)
  if nodeName is None: name = AdminControl.getCell()
  else: name = nodeName
  params = ['-name', name, '-direction', direction, '-scopeName', scopeName, '-certificateAlias', certAlias, '-sslConfigAliasName', sslConfigAlias, '-sslConfigScopeName', scopeName]
  try:
    AdminTask.modifySSLConfigGroup(params)
  except:
    warnings.append('Failed: {0} in {1} {2} {3}'.format(certAlias, scopeName, sslConfigAlias, direction))
    return False, warnings
  if AdminConfig.hasChanges():
    warnings.append('Modified: {0} in {1} {2} {3}'.format(certAlias, scopeName, sslConfigAlias, direction))
    return True, warnings
  warnings.append('Unchanged: {0} {1} {2} {3}'.format(certAlias, scopeName, sslConfigAlias, direction))
  return False, warnings
 
def restartAllNodeAgents(warnings=[]):
  changed = False
  nodeIds = AdminConfig.list('Node').split('\n')
  for nodeId in nodeIds:
    nodeName = AdminConfig.showAttribute(nodeId, 'name')
    reply, warnings = restartNodeAgent(nodeName, warnings)
    if reply: changed = True
  return changed, warnings
  
def restartNodeAgent(nodeName, warnings=[]):
  mbeanSpec = AdminControl.completeObjectName('node={0},type=NodeAgent,*'.format(nodeName))
  if len(mbeanSpec) == 0: return False, warnings
  try:
    AdminControl.invoke(mbeanSpec, 'restart', '[false false]')
  except:
    warnings.append('Failed: Nodeagent {0}'.format(nodeName))
    return False, warnings
  warnings.append('Restarted: NodeAgent {0}'.format(nodeName))
  return True, warnings

def setNodeVariable(nodeName, symbolicName, value, warnings=[]):
  notFound = True
  node = AdminConfig.getid("/Node:{0}/".format(nodeName))
  varSubstitutions = AdminConfig.list("VariableSubstitutionEntry", node).split(java.lang.System.getProperty("line.separator"))
  for varSubst in varSubstitutions:
    getVarName = AdminConfig.showAttribute(varSubst, "symbolicName")
    if getVarName == symbolicName:
      notFound = False
      AdminConfig.modify(varSubst, [["value", value]])
      break
  if notFound:
    warnings.append('Not found: {0} in {1}'.format(symbolicName, nodeName))
    return False, warnings
  if AdminConfig.hasChanges():
    warnings.append('Modified: {0} in {1} {2}'.format(symbolicName, nodeName, value))
    return True, warnings
  warnings.append('Unchanged: {0} in {1} {2}'.format(symbolicName, nodeName, value))
  return False, warnings

def createSharedLibrary(name, classPath, description, warnings=[]):
  cellName = AdminControl.getCell()
  cellId = AdminConfig.getid(getIdSpec(cellName, 'Cell'))
  libraryId = AdminConfig.getid(getIdSpec(name, 'Library'))
  if libraryId == '':
    params = [['name', name], ['classPath', classPath], ['description', description]]
    AdminConfig.create('Library', cellId, params)
    warnings.append('Created library: {0}'.format(name))
    return True, warnings
  warnings.append('Libary exists: {0}'.format(name))
  return False, warnings

def mapSharedLibraries(appName, moduleName, moduleUri, sharedLibraries, warnings=[]):
  moduleParams = [ moduleName, moduleUri, '+'.join(sharedLibraries)]
  params = ['-MapSharedLibForMod', [moduleParams]]
  AdminApp.edit(appName, params)
  if AdminConfig.hasChanges():
    warnings.append('Modified: {0} in {1}'.format(moduleName, appName))
    return True, warnings
  warnings.append('Unchanged: {0} in {1}'.format(moduleName, appName))
  return False, warnings

def createUnmanagedNode(nodeName, hostName, nodeOs='linux', warnings=[]):
  nodeList = AdminTask.listNodes()
  if nodeName in nodeList:
    warnings.append('Exists: {0}'.format(nodeName))
    return False, warnings
  AdminTask.createUnmanagedNode(['-nodeName', nodeName, '-hostName', hostName, '-nodeOperatingSystem', nodeOs])
  warnings.append('Created: {0} on {1}'.format(nodeName, hostName))
  return True, warnings

def createWebServer(nodeName, name, webInstallRoot, pluginInstallRoot, webPort='80', adminUserID=None, adminPasswd=None, adminPort='8008', adminProtocol='HTTP', warnings=[]):
  serverList = AdminTask.listServers(['-serverType', 'WEB_SERVER'])
  if name in serverList:
    warnings.append('Exists: {0}'.format(name))
    return False, warnings
  serverConfig = ['-webPort', webPort, '-webInstallRoot', webInstallRoot, '-webProtocol', 'HTTP', '-pluginInstallRoot', pluginInstallRoot, '-webAppMapping', 'ALL'] 
  remoteServerConfig = ['-adminPort', adminPort]
  if adminUserID is not None and adminUserID != '':
    remoteServerConfig.append('-adminUserID')
    remoteServerConfig.append(adminUserID)
  if adminPasswd is not None and adminPasswd != '':
    remoteServerConfig.append('-adminPasswd')
    remoteServerConfig.append(adminPasswd)
  remoteServerConfig.append('-adminProtocol')
  remoteServerConfig.append(adminProtocol)
  try:
    AdminTask.createWebServer(nodeName, ['-name', name, '-templateName', 'IHS', '-serverConfig', serverConfig, '-remoteServerConfig', remoteServerConfig])
  except Exception as e:
    # message = str(e)
    # print(message)
    # warnings.append('Exception: {0}'.format(str(e)))
    warnings.append('Failed: {0} {1}'.format(json.dumps(serverConfig), json.dumps(remoteServerConfig)))
    return False, warnings
  warnings.append('Created: {0} on {1}'.format(name, nodeName))
  return True, warnings

def mapClusterAppWebModuleToServers(appName, clusterName, moduleName, serverList):
  cellName = AdminControl.getCell()

# AdminApp.edit('ITIM', 
# '[ -MapModulesToServers [
# [ ITIM_Self_Service itim_self_service.war,WEB-INF/web.xml WebSphere:cell=ITIM_CELL,cluster=itimCluster+WebSphere:cell=ITIM_CELL,node=ihs1,server=webServer1 ]
# [ "ITIM Self Service Help" itim_self_service_help.war,WEB-INF/web.xml
#  WebSphere:cell=ITIM_CELL,cluster=itimCluster+WebSphere:cell=ITIM_CELL,node=ihs1,server=webServer1 ]
# ]
# ]' )  
# AdminConfig.modify('(cells/ITIM_CELL/nodes/ihs1/servers/webServer1|server.xml#WebServer_1675236214259)',
#  '[[logFilenameAccess "/var/log/httpd/access.log"] [logFilenameError "/var/log/httpd/error.log"]]') 
# AdminTask.importCertificate('[-keyFilePath /opt/ibm/WebSphere/AppServer/profiles/Dmgr01/etc/idm10app2u.p12 -keyFilePassword ******** -keyFileType PKCS12 -certificateAliasFromKeyFile idm10app2u -keyStoreName NodeDefaultKeyStore -keyStoreScope (cell):ITIM_CELL:(node):node2 ]') 

# AdminTask.editCompUnit('[-cuID WebSphere:cuname=isc_CU.eba -blaID WebSphere:blaname=com.ibm.isim_BLA -MapTargets [[ebaDeploymentUnit WebSphere:node=node2,server=webServer2+WebSphere:cluster=itimCluster]]]')
# AdminTask.editCompUnit('[-cuID WebSphere:cuname=isc_CU.eba -blaID WebSphere:blaname=com.ibm.isim_BLA ]') 
