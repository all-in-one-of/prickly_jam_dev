# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import maya.cmds as cmds
import pymel.core as pm
import os 
import re

import tank

from tank import Hook
from tank import TankError

import sgtk

# need the engine to access templates for publishing
from tank.platform.engine import current_engine

class ScanSceneHook(Hook):
    """
    Hook to scan scene for items to publish
    """

    def execute(self, **kwargs):
        """
        Main hook entry point
        :returns:       A list of any items that were found to be published.
                        Each item in the list should be a dictionary containing
                        the following keys:
                        {
                            type:   String
                                    This should match a scene_item_type defined in
                                    one of the outputs in the configuration and is
                                    used to determine the outputs that should be
                                    published for the item

                            name:   String
                                    Name to use for the item in the UI

                            description:    String
                                            Description of the item to use in the UI

                            selected:       Bool
                                            Initial selected state of item in the UI.
                                            Items are selected by default.

                            required:       Bool
                                            Required state of item in the UI.  If True then
                                            item will not be deselectable.  Items are not
                                            required by default.

                            other_params:   Dictionary
                                            Optional dictionary that will be passed to the
                                            pre-publish and publish hooks
                        }
        """

        items = []

        # get the main scene:

        scene_name = cmds.file(query=True, sn=True)

        if not scene_name:
            raise TankError("Please Save your file before Publishing")

        scene_path = os.path.abspath(scene_name)
        name = os.path.basename(scene_path)

        # create the primary item - this will match the primary output 'scene_item_type':
        items.append({"type": "work_file", "name": name})

        engine = tank.platform.current_engine()
        # get the current app
        app = self.parent

        work_template = app.get_template("template_work")
        work_template_fields = work_template.get_fields(scene_name)


        # Revilo - look for cameras to publish based on MDS metadata:
        print work_template_fields
        if 'Step' in work_template_fields:
            if work_template_fields['Step'].lower() == 'track':
                for camera in cmds.listCameras(perspective=True):
                    if cmds.attributeQuery('mdsMetadata', n=camera, exists=True):

                        # Evaluate shutterAngle Settings
                        subFrame = cmds.getAttr(camera + ".subframe")

                        if subFrame == 0:
                            shutterAngle = 0.25
                        if subFrame == 1:
                            shutterAngle = 0.2
                        if subFrame == 2:
                            shutterAngle = 0.125

                        items.append({"type": "camera", "name": camera, "shutterAngle": shutterAngle})


        # exporting clean maya scene for modeling
        eng = sgtk.platform.current_engine()
        ctx = eng.context

        if ctx.entity['type'] == 'Asset':
            if ctx.step['name'] == 'Model':

                #find mds tagged groups.

                for geo in cmds.ls(type="transform", long=True):
                    # Geo found - does it have a tag?
                    if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):
                    # Tag found - Let's define a name for geo called <Asset/Shot>_<Step>
                        geoName = geo.strip("|")
                        
                        vray_disp_nodes = get_vray_displacement_nodes(geo)

                        import pprint
                        print pprint.pformat(vray_disp_nodes, indent=4)
                        items.append({"type": "maya_model", "name": geoName, 'vray_disp_nodes': vray_disp_nodes})

            if ctx.step['name'] == 'Surface':
                #find mds tagged groups.
                for geo in cmds.ls(type="transform", long=True):
                    # Geo found - does it have a tag?
                    if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):
                    # Tag found - Let's define a name for geo called <Asset/Shot>_<Step>
                        geoName = geo.strip("|")

                        file_nodes = get_file_nodes(geo)
                        non_ref_file_nodes = []


                        for i in cmds.ls(type='mesh'):
                            shadingEngines = pm.listConnections(i, type='shadingEngine')
                            usedTextureNodes = pm.listHistory(shadingEngines, type='file')
                            print usedTextureNodes
    
                        for file_node in file_nodes:
                            if not cmds.referenceQuery(file_node['file_node'], inr=True):
                                non_ref_file_nodes.append(file_node)

                        import pprint
                        print pprint.pformat(non_ref_file_nodes, indent=4)
                        items.append({"type": "maya_surface", "name": geoName, 'file_nodes': non_ref_file_nodes})


            if ctx.step['name'] == 'Rig':
                for geo in cmds.ls(type="transform", long=True):
                    # Geo found - does it have a tag?
                    if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):
                    # Tag found - Let's define a name for geo called <Asset/Shot>_<Step>
                        geoName = geo.split("|")[1]
                        
                        items.append({"type": "maya_rig", "name": geoName})
                pass
            # # If asset publish individual alembics 
            # print '=============='
            # print 'Asset level alembic'
            # print '=============='
            # for geo in cmds.ls(assemblies=True, long=True):
            #     alembic_caches = {}
            #     if cmds.ls(geo, dag=True, type="mesh"):

            #         # Geo found - does it have a tag?
            #         if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):

            #             # Tag found - Let's define a name for geo called <Asset/Shot>_<Step>
            #             geoName = geo.strip("|")

            #             # Evaluate shutterAngle attributes
            #             subFrame = cmds.getAttr(geo + ".subframe")

            #             if subFrame == 0:
            #                 shutterAngle = 0.25
            #             if subFrame == 1:
            #                 shutterAngle = 0.2
            #             if subFrame == 2:
            #                 shutterAngle = 0.125

            #             alembic_caches[geo] = {"selection" : geo, "shutterAngle": shutterAngle, 'group_name': geoName}
            #             # include this group as a 'mesh_group', record the selection, the name and the shutterAngle
            #             print 'Adding asset alembic'
            #             items.append({"type": "alembic_cache", "name": geoName, 'caches': alembic_caches})


        # If shot publish a group of alembics    
        if ctx.entity['type'] == 'Shot':

            if ctx.step['name'].lower() == 'anim':
                alembic_caches = None
                for geo in cmds.ls(type="transform", long=True):
                    if cmds.ls(geo, dag=True, type="transform"):
                        # Geo found - does it have a tag?
                        if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):

                            found_cam =False
                            for i in cmds.listRelatives(geo, c=True):
                                if cmds.nodeType(i) == 'camera':
                                    found_cam = True

                            if not found_cam:
                                # Tag found - Let's define a name for geo called <Asset/Shot>_<Step>
                                geoName = geo.strip("|")

                                # Evaluate shutterAngle attributes
                                subFrame = cmds.getAttr(geo + ".subframe")

                                if subFrame == 0:
                                    shutterAngle = 0.25
                                if subFrame == 1:
                                    shutterAngle = 0.2
                                if subFrame == 2:
                                    shutterAngle = 0.125

                                if alembic_caches is None:
                                    alembic_caches = {}

                                alembic_caches[geo] = {"selection" : geo, "shutterAngle": shutterAngle, 'group_name': geoName}
                            # include this group as a 'mesh_group', record the selection, the name and the shutterAngle
                if alembic_caches is not None:
                    items.append({"is_shot": True, "type": "alembic_cache", "name": 'alembic_caches', 'caches': alembic_caches})

        # Added by: Chet
        # Date: 18/05/2018
        # Project: otherside

        # Added a secondary publish for geometry caches

        # geo_caches = {}
        # for geo in cmds.ls(assemblies=True, long=True):
        #     # Geo found - does it have a tag?
        #     if cmds.attributeQuery('mdsMetadata', n=geo, exists=True):
        #         meshes = cmds.listRelatives(geo, ad=True, type='mesh', pa=True)
        #         visible_meshes = []
        #         for mesh in meshes:
        #             if cmds.getAttr(cmds.listRelatives(mesh, p=True)[0] + '.visibility'):
        #                 visible_meshes.append(mesh)
        #         geo_caches[geo] = visible_meshes
        
        # items.append({'type': 'geometry_cache', 'name': 'geo_caches', 'caches': geo_caches})

        # Tony - look for renders:      
        # we'll use the engine to get the templates

        engine = tank.platform.current_engine()

        # get the current app
        app = self.parent

        # look up the template for the work file in the configuration
        # will get the proper template based on context (Asset, Shot, etc)


        if 'Step' in work_template_fields:

            if work_template_fields['Step'] == 'light':
                version = work_template_fields["version"]
                # get all the secondary output render templates and match them against
                # what is on disk
                secondary_outputs = app.get_setting("secondary_outputs")
                render_outputs = [out for out in secondary_outputs if out["tank_type"] == "Rendered Image"]
                for render_output in render_outputs:
                    render_template = app.get_template_by_name(render_output["publish_template"])
                    # now look for rendered images. note that the cameras returned from 
                    # listCameras will include full DAG path. You may need to account 
                    # for this in your, more robust solution, if you want the camera name
                    # to be part of the publish path. For my simple test, the cameras 
                    # are not parented, so there is no hierarchy.

                    # iterate over all cameras and layers
                    for layer in cmds.renderSetup(q=True, renderLayers=True):
                            # apparently maya has 2 names for the default layer. I'm
                            # guessing it actually renders out as 'masterLayer'.
                            layer = layer.replace("defaultRenderLayer", "masterLayer")
                            # these are the fields to populate into the template to match
                            # against
                            fields = {
                                'Shot': work_template_fields['Shot'],
                                'Step': work_template_fields['Step'],
                                'maya.layer_name': layer,
                                'version': version,
                            }
                            # match existing paths against the render template
                            paths = engine.tank.abstract_paths_from_template(
                                render_template, fields)
                            # if there's a match, add an item to the render 
                            if paths:
                                items.append({
                                    "type": "rendered_image",
                                    "layer": layer,
                                    "name": work_template_fields['Shot'] + '_' +
                                            work_template_fields['Step'] + '_' +
                                            layer + '_v'  +
                                            str(version).zfill(3),

                                # since we already know the path, pass it along for
                                # publish hook to use
                                "other_params": {
                                    # just adding first path here. may want to do some
                                    # additional validation if there are multiple.
                                    'path': paths[0],
                                }
                            })
        for i in items:
            print i
        return items

###################################
# UTILITY FUNCTIONS
###################################

def get_connected_file_nodes(node):
    return cmds.ls( cmds.listHistory(node), type = 'file' )

def uses_udims(path, file_node):
    if '<udim>' in path.lower():
        return True

    pattern = re.compile('(.*)(\d{4})(.*)')
    result = pattern.match(path)
    if result:
        return True

def match_udim_texture(texture_path, file_path):
    texture = texture_path.split('/')[-1].lower()
    filename = file_path.split('/')[-1].lower()

    if '<udim>' in texture:
        pattern = re.compile('(.*)(<udim>)(.*)')
    else:
        pattern = re.compile('(.*)(\d{4})(.*)')
    file_pattern = re.compile('(.*)(\d{4})(.*)')
    texture_result = pattern.match(texture)
    filename_result = file_pattern.match(filename)

    if texture_result and filename_result:

        if texture_result.group(1) == filename_result.group(1) and texture_result.group(3) == filename_result.group(3):
            return True

def get_textures(file_node):
    texture_name = cmds.getAttr('%s.%s' % (file_node, 'fileTextureName'))
    
    if uses_udims(texture_name, file_node):
        textures = []
        texture_root_dir = os.path.dirname(texture_name)
        if os.path.exists(texture_root_dir):
            #search this direcotry
            for i in os.listdir(texture_root_dir):
                if match_udim_texture(texture_name, i):
                    textures.append(texture_root_dir + '/' +i)
        else:
            project_path = cmds.workspace(rd=True, q=True)
            texture_root_dir = project_path + texture_root_dir
            if os.path.exists(texture_root_dir):
                for i in os.listdir(texture_root_dir):
                    if match_udim_texture(texture_name, i):
                        textures.append(texture_root_dir + '/' +i)
        return textures

    else:
        #Not Using Udims
        if os.path.exists(texture_name.replace('/', os.path.sep)):
            return [texture_name]
        else:
            project_path = cmds.workspace(rd=True, q=True)
            return [project_path + texture_name]
            #if os.path.exists():
            #    print '%s exists' % os.path.join(project_path.replace('/', os.path.sep), texture_name.replace('/', os.path.sep))

def get_file_nodes(node):

    file_nodes = cmds.ls(type = 'file')

    exports = []
    for i in file_nodes:
        textures = get_textures(i)
        exports.append(
            {'file_node': i,
             'fileTextureName':cmds.getAttr('%s.%s' % (i, 'fileTextureName')),
             'texture_paths': textures
                }
            )
    return exports


def get_vray_displacement_nodes(node):

    trans = cmds.listRelatives(node, ad=True, type='transform')

    all_vray_disp_nodes = cmds.ls(type = 'VRayDisplacement')
    vray_disp_nodes = []

    for vray_disp_node in all_vray_disp_nodes:
        members = cmds.sets( vray_disp_node, q=True, no=True)
        for member in members:
            if member in trans:
                vray_disp_nodes.append(vray_disp_node)
                break

    exports = []
    
    for i in vray_disp_nodes:
        file_nodes = get_connected_file_nodes(i)
        texture_nodes = []
        for file_node in file_nodes:
            textures = get_textures(file_node)
            texture_nodes.append(
                {'file_node': file_node,
                 'fileTextureName':cmds.getAttr('%s.%s' % (file_node, 'fileTextureName')),
                 'texture_paths': textures
                    }
                )
        exports.append({'vray_disp_node': i, 'texture_nodes':texture_nodes})
    return exports
