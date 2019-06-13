# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type. 
"""
import sgtk
import os
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

HookBaseClass = sgtk.get_hook_baseclass()

class MayaActions(HookBaseClass):
    
    ##############################################################################################################
    # public interface - to be overridden by deriving classes 
    
    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.
    
        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.
        
        The hook should return at least one action for each item passed in via the 
        actions parameter.
        
        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.
        
        Because you are operating on a particular publish, you may tailor the output 
        (caption, tooltip etc) to contain custom information suitable for this publish.
        
        The ui_area parameter is a string and indicates where the publish is to be shown. 
        - If it will be shown in the main browsing area, "main" is passed. 
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed. 
        
        Please note that it is perfectly possible to create more than one action "instance" for 
        an action! You can for example do scene introspection - if the action passed in 
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than 
        one object is returned for an action, use the params key to pass additional 
        data into the run_action hook.
        
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))
        
        action_instances = []
        
        if "reference" in actions:
            action_instances.append( {"name": "reference", 
                                      "params": None,
                                      "caption": "Create Reference", 
                                      "description": "This will add the item to the scene as a standard reference."} )
   
        if "reference_custom_namespace" in actions:
            action_instances.append( {"name": "reference_custom_namespace", 
                                      "params": None,
                                      "caption": "Create Reference Custom Namespace", 
                                      "description": "This will add the item to the scene as a standard reference with a custom namespace."} )

        if "import_geo_cache" in actions:
            action_instances.append( {"name": "import_geo_cache", 
                                      "params": None,
                                      "caption": "Import Geometry Caches", 
                                      "description": "This will import the geometry caches for the shot."} )
        if "import_alembic_cache" in actions:
            action_instances.append( {"name": "import_alembic_cache", 
                                      "params": None,
                                      "caption": "Import Alembic Caches", 
                                      "description": "This will import the alembic caches for the shot."} )

        if "reference_alembic_cache" in actions:
            action_instances.append( {"name": "reference_alembic_cache", 
                                      "params": None,
                                      "caption": "Reference Alembic Caches", 
                                      "description": "This will reference the alembic caches for the shot."} )

        if "import" in actions:
            action_instances.append( {"name": "import", 
                                      "params": None,
                                      "caption": "Import into Scene", 
                                      "description": "This will import the item into the current scene."} )

        if "import_multi" in actions:
            action_instances.append( {"name": "import_multi", 
                                      "params": None,
                                      "caption": "Import multiple into Scene", 
                                      "description": "This will import multiple copies of item into the current scene."} )

        if "reference_multi" in actions:
            action_instances.append( {"name": "reference_multi", 
                                      "params": None,
                                      "caption": "Reference multiple into Scene", 
                                      "description": "This will reference multiple copies of item into the current scene."} )
        if "texture_node" in actions:
            action_instances.append( {"name": "texture_node",
                                      "params": None, 
                                      "caption": "Create Texture Node", 
                                      "description": "Creates a file texture node for the selected item.."} )
            
        if "udim_texture_node" in actions:
            # Special case handling for Mari UDIM textures as these currently only load into 
            # Maya 2015 in a nice way!
            if self._get_maya_version() >= 2015:
                action_instances.append( {"name": "udim_texture_node",
                                          "params": None, 
                                          "caption": "Create Texture Node", 
                                          "description": "Creates a file texture node for the selected item.."} )    
        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the ``execute_action``
            method for backward compatibility with hooks written for the previous
            version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an error
            is raised midway through.

        :param list actions: Action dictionaries.
        """
        for single_action in actions:
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]
            self.execute_action(name, params, sg_publish_data)

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.
        
        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))
        
        # resolve path
        # toolkit uses utf-8 encoded strings internally and Maya API expects unicode
        # so convert the path to ensure filenames containing complex characters are supported
        path = self.get_publish_path(sg_publish_data).decode("utf-8")
        
        if name == "reference":
            self._create_reference(path, sg_publish_data)

        if name == "reference_custom_namespace":
            self._create_reference_custom_ns(path, sg_publish_data)

        if name == "import":
            self._do_import(path, sg_publish_data)
        
        if name == "import_multi":
            self._do_import_multi(path, sg_publish_data)

        if name == "reference_multi":
            self._create_reference_multi(path, sg_publish_data)

        if name == "import_geo_cache":
            self._do_import_geo_cache(path, sg_publish_data)

        if name == "reference_alembic_cache":
            self._do_reference_alembic_cache(path, sg_publish_data)

        if name == "import_alembic_cache":
            self._do_import_alembic_cache(path, sg_publish_data)

        if name == "texture_node":
            self._create_texture_node(path, sg_publish_data)
            
        if name == "udim_texture_node":
            self._create_udim_texture_node(path, sg_publish_data)
                        
           
    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behaviour of things
    
    def _create_reference(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody

        namespace = ':'

        if self.parent.engine.context.step['name'] == 'Layout':

            count = 1
            namespace_found = False
            all_namespaces = cmds.namespaceInfo(lon=True)

            while not namespace_found:
                namespace = '%s_%03d' % (sg_publish_data.get("entity").get("name"), count)
                if namespace in all_namespaces:
                    count += 1
                else:
                    namespace_found=True
                    break
        else:
            namespace = ':'

        pm.system.createReference(path, 
                                  loadReferenceDepth= "all", 
                                  mergeNamespacesOnClash=True, 
                                  namespace=namespace,
                                  sharedNodes="renderLayersByName")

    def _create_reference_custom_ns(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody

        namespace = ':'

        result = cmds.promptDialog(
                        title='Custom Namespace',
                        message='Enter Namespace:',
                        button=['OK', 'Cancel'],
                        defaultButton='OK',
                        cancelButton='Cancel',
                        dismissString='Cancel')

        if result == 'OK':
            namespace = cmds.promptDialog(query=True, text=True)

        pm.system.createReference(path, 
                                  loadReferenceDepth= "all", 
                                  mergeNamespacesOnClash=True, 
                                  namespace=namespace,
                                  sharedNodes="renderLayersByName")


    def _create_reference_multi(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        currEngine = sgtk.platform.current_engine()

        # Get geometry path for anime caches
        tk = currEngine.tank
        temp1 = tk.templates["maya_shot_geometry_cache_location"]
        fields = currEngine.context.as_template_fields(temp1)
        fields['Step'] = 'anim'
        geo_cache_path = temp1.apply_fields(fields)

        # Get find group name of loading asset

        temp2 = tk.templates["maya_asset_publish"]
        ctx = tk.context_from_path(path)
        fields = ctx.as_template_fields(temp2)
        group_name = fields['Asset']

        count = 0
        if os.path.exists(geo_cache_path):
            for i in os.listdir(geo_cache_path):
                if group_name in i and '.xml' in i:
                    count += 1
        if count == 0:
            count = 1

        result = cmds.promptDialog(
            title='Reference Multi',
            message='Enter Number:',
            button=['OK', 'Cancel'],
            defaultButton='OK',
            cancelButton='Cancel',
            dismissString='Cancel',
            text=count
            )
        
        if result == 'OK':
            num_of_refs = int(cmds.promptDialog(query=True, text=True))
            
            for i in range(0,num_of_refs): 
                    # make a name space out of entity name + publish name
                    # e.g. bunny_upperbody                

                    if self.parent.engine.context.step['name'] == 'Layout':
                        namespace = "%s" % sg_publish_data.get("entity").get("name")
                        namespace = namespace.replace(" ", "_")
                    else:
                        namespace = ':'


                    pm.system.createReference(path, 
                              loadReferenceDepth= "all", 
                              mergeNamespacesOnClash=True, 
                              namespace=namespace,
                              sharedNodes="renderLayersByName")

    def _do_import_geo_cache(self, path, sg_publish_data):
        for cache in os.listdir(path):
            if cache.endswith('.xml'):
                group_name = cache.split('.xml')[0]
                try:
                    meshes = cmds.listRelatives(group_name, ad=True, type='mesh',pa=True)
                    unconnected_meshes = []
                    for mesh in meshes:
                        conns = cmds.listConnections(mesh)
                        not_connected = True
                        for con in conns:
                            if 'cacheSwitch' in con or 'historySwitch' in con:
                                not_connected = False
                        if not_connected:
                            unconnected_meshes.append(mesh)
                    cmds.select(unconnected_meshes, cl=True)
                    cache_path = path.replace('\\', '/') + '/' + cache
                    if len(unconnected_meshes) > 0:
                        pm.mel.doImportCacheFile(cache_path, "mcx", unconnected_meshes, list())
                except:
                    print 'No mesh found for cache: {}'.format(cache)


    def _do_import_alembic_cache(self, path, sg_publish_data):
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        import pprint 
        print '================================'
        print '================================'
        print pprint.pformat(sg_publish_data, indent=4)
        print '================================'
        print '================================'

        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        for cache in os.listdir(path):

            alembic_nodes = cmds.ls(type='AlembicNode')
            alembic_paths = []
            for alembic_node in alembic_nodes:
                alembic_paths.append(cmds.getAttr('%s.%s' % (alembic_node, 'abc_File')))

            if not os.path.join(path,cache).replace('\\', '/' ) in alembic_paths:

                # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
                try:
                    namespace = ('_').join(cache.split('.')[0].split('_')[-2:])
                    print namespace
                except Exception as e:
                    print e
                    namespace = ':'

                if namespace == '':
                    namespace = ':'
                
                print 'namespace = %s' % namespace

                asset_name = namespace.split('_')[0]

                # eng = sgtk.platform.current_engine()
                # sg = eng.shotgun
                # project = eng.context.project

                # try:
                #     asset = sg.find_one('Asset', [['code', 'is', asset_name]] )

                #     fields = ['id', 'version_number', 'code', 'path']
                #     sorting = [{'column':'version_number','direction':'desc'}]
                #     filters = [
                #                 ['project', 'is', project],
                #                 ['published_file_type', 'is', {'type': 'PublishedFileType', 'id': 117}],
                #                 ['entity', 'is', asset]
                #                 ]

                #     result = sg.find('PublishedFile', filters, fields)
                #     latest_surfacing = None
                #     if result:
                #         latest_surfacing = result[-1]
                # except Exception as e:
                #     print 'Could not find surfacing for asset:%s' % asset_name
                #     print e
                #     latest_surfacing = None

                # print '--------------'
                # print latest_surfacing
                # print '--------------'

                try:
                    nodes = cmds.file(os.path.join(path,cache), i=True, renameAll=True, namespace=namespace, loadReferenceDepth="all", preserveReferences=True, rnn=True)
                except Exception as e:
                    print e
                    print 'Failed to load alebmic: %s' % os.path.join(path,cache)

                # print '============'
                # alembic_root = None

                # trans = []

                # for n in nodes:
                #     if cmds.listRelatives(n, children=True, fullPath=True, type='mesh'):
                #         trans.append(n)

                # alembic_root = ["|".join(n.split("|")[:2]) for n in trans]
                # alembic_root = list(set(alembic_root))
                
                # print '============'
                # print 'alembic_root=%s' % alembic_root
                # print '============'

                # namespace += '_surface'
                # if not latest_surfacing is None:
                #     nodes = cmds.file(os.path.join(path,latest_surfacing['path']['local_path'].replace('\\', '/')), i=True, renameAll=True, namespace=namespace, loadReferenceDepth="all", preserveReferences=True, rnn=True)
                #     for n in nodes:
                #         if cmds.attributeQuery('mdsMetadata', n=n, exists=True):
                #             surface_root = n

                #     print '============'
                #     print 'surface_root=%s' % surface_root
                #     print '============'

                #     if not surface_root is None and not alembic_root is None:
                #         cmds.select(cl=True)
                #         cmds.select(alembic_root)
                #         cmds.select(surface_root, add=True)
                #         blend_node = cmds.blendShape(origin='world', weight=(0,1))

                # cmds.hide(alembic_root)
            else:
                print 'Skipping\n\t%s\nAs it is alrady loaded.' % os.path.join(path,cache)

    def _do_reference_alembic_cache(self, path, sg_publish_data):
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
                
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody
        for cache in os.listdir(path):
            # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
            pm.system.createReference(cache, 
                                  loadReferenceDepth= "all", 
                                  mergeNamespacesOnClash=True, 
                                  namespace=":",
                                  sharedNodes="renderLayersByName")

    def _do_import(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
                
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")
        
        # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
        cmds.file(path, i=True, renameAll=True, namespace=':', loadReferenceDepth="all", preserveReferences=True)
            

    def _do_import_multi(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)


        currEngine = sgtk.platform.current_engine()

        # Get geometry path for anime caches
        tk = currEngine.tank
        temp1 = tk.templates["maya_shot_geometry_cache_location"]
        fields = currEngine.context.as_template_fields(temp1)
        fields['Step'] = 'anim'
        geo_cache_path = temp1.apply_fields(fields)
        print geo_cache_path

        # Get find group name of loading asset

        temp2 = tk.templates["maya_asset_publish"]
        ctx = tk.context_from_path(path)
        fields = ctx.as_template_fields(temp2)
        group_name = fields['Asset']

        count = 0
        if os.path.exists(geo_cache_path):
            for i in os.listdir(geo_cache_path):
                if group_name in i and '.xml' in i:
                    count += 1
                    print i
        if count == 0:
            count = 1

        result = cmds.promptDialog(
            title='Import Multi',
            message='Enter Number:',
            button=['OK', 'Cancel'],
            defaultButton='OK',
            cancelButton='Cancel',
            dismissString='Cancel',
            text=count
            )
        
        if result == 'OK':
            num_of_imports = int(cmds.promptDialog(query=True, text=True))
            
            for i in range(0,num_of_imports):                        
                # make a name space out of entity name + publish name
                # e.g. bunny_upperbody                
                namespace = "%s" % sg_publish_data.get("entity").get("name")
                namespace = namespace.replace(" ", "_")

                # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
                cmds.file(path, i=True, renameAll=True, namespace=':', loadReferenceDepth="all", preserveReferences=True)

    def _create_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """
        file_node = cmds.shadingNode('file', asTexture=True)
        cmds.setAttr( "%s.fileTextureName" % file_node, path, type="string" )
        return file_node

    def _create_udim_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a UDIM (Mari) texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """
        # create the normal file node:
        file_node = self._create_texture_node(path, sg_publish_data)
        if file_node:
            # path is a UDIM sequence so set the uv tiling mode to 3 ('UDIM (Mari)')
            cmds.setAttr("%s.uvTilingMode" % file_node, 3)
            # and generate a preview:
            mel.eval("generateUvTilePreview %s" % file_node)
        return file_node
            
    def _get_maya_version(self):
        """
        Determine and return the Maya version as an integer
        
        :returns:    The Maya major version
        """
        if not hasattr(self, "_maya_major_version"):
            self._maya_major_version = 0
            # get the maya version string:
            maya_ver = cmds.about(version=True)
            # handle a couple of different formats: 'Maya XXXX' & 'XXXX':
            if maya_ver.startswith("Maya "):
                maya_ver = maya_ver[5:]
            # strip of any extra stuff including decimals:
            major_version_number_str = maya_ver.split(" ")[0].split(".")[0]
            if major_version_number_str and major_version_number_str.isdigit():
                self._maya_major_version = int(major_version_number_str)
        return self._maya_major_version
        
