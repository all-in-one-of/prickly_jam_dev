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
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError

# Revilo - Added Import
import re
# added Tony
from distutils.dir_util import copy_tree
from os import walk

class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """
    def execute(
        self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task,
        primary_publish_path, progress_cb, user_data, **kwargs):
        """
        Main hook entry point
        :param tasks:                   List of secondary tasks to be published.  Each task is a
                                        dictionary containing the following keys:
                                        {
                                            item:   Dictionary
                                                    This is the item returned by the scan hook
                                                    {
                                                        name:           String
                                                        description:    String
                                                        type:           String
                                                        other_params:   Dictionary
                                                    }

                                            output: Dictionary
                                                    This is the output as defined in the configuration - the
                                                    primary output will always be named 'primary'
                                                    {
                                                        name:             String
                                                        publish_template: template
                                                        tank_type:        String
                                                    }
                                        }

        :param work_template:           template
                                        This is the template defined in the config that
                                        represents the current work file

        :param comment:                 String
                                        The comment provided for the publish

        :param thumbnail:               Path string
                                        The default thumbnail provided for the publish

        :param sg_task:                 Dictionary (shotgun entity description)
                                        The shotgun task to use for the publish

        :param primary_publish_path:    Path string
                                        This is the path of the primary published file as returned
                                        by the primary publish hook

        :param progress_cb:             Function
                                        A progress callback to log progress during pre-publish.  Call:

                                            progress_cb(percentage, msg)

                                        to report progress to the UI

        :param primary_task:            The primary task that was published by the primary publish hook.  Passed
                                        in here for reference.  This is a dictionary in the same format as the
                                        secondary tasks above.

        :param user_data:               A dictionary containing any data shared by other hooks run prior to
                                        this hook. Additional data may be added to this dictionary that will
                                        then be accessible from user_data in any hooks run after this one.

        :returns:                       A list of any tasks that had problems that need to be reported
                                        in the UI.  Each item in the list should be a dictionary containing
                                        the following keys:
                                        {
                                            task:   Dictionary
                                                    This is the task that was passed into the hook and
                                                    should not be modified
                                                    {
                                                        item:...
                                                        output:...
                                                    }

                                            errors: List
                                                    A list of error messages (strings) to report
                                        }
        """
        results = []
        

        # publish all tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            progress_cb(0, "Publishing", task)

            # Revilo - Added geo alembic publishing
            if output["name"] == "alembic_cache":
                try:
                   self.__publish_alembic_cache(
                        item,
                        output,
                        work_template,
                        primary_publish_path,
                        sg_task,
                        comment,
                        thumbnail_path,
                        progress_cb,
                    )
                except Exception, e:
                   errors.append("Publish failed - %s" % e)

            # Revilo - Added camera alembic publishing
            elif output["name"] == "camera":
                try:
                    self.__publish_camera(
                        item,
                        output,
                        work_template,
                        primary_publish_path,
                        sg_task,
                        comment,
                        thumbnail_path,
                        progress_cb,
                    )
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            elif output["name"] == "maya_model":
                try:
                    self.__publish_maya_model(
                        item,
                        output,
                        work_template,
                        primary_publish_path,
                        sg_task,
                        comment,
                        thumbnail_path,
                        progress_cb,
                    )
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            elif output["name"] == "maya_surface":
                try:
                    self.__publish_maya_surface(
                        item,
                        output,
                        work_template,
                        primary_publish_path,
                        sg_task,
                        comment,
                        thumbnail_path,
                        progress_cb,
                    )
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            elif output["name"] == "maya_rig":
                try:
                    self.__publish_maya_rig(
                        item,
                        output,
                        work_template,
                        primary_publish_path,
                        sg_task,
                        comment,
                        thumbnail_path,
                        progress_cb,
                    )
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            # Tony - Added Rendered images from maya
            elif output["name"] == "rendered_image":
                try:
                    self.__publish_rendered_images(item, output,
                        work_template, primary_publish_path, sg_task, comment,
                        thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            else:
                 # don't know how to publish this output types!
                 errors.append("Don't know how to publish this item!")


            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task":task, "errors":errors})

            progress_cb(100)


        return results

    def __publish_maya_rig(self, item, output, work_template, primary_publish_path,
                                        sg_task, comment, thumbnail_path, progress_cb):

        progress_cb(10, "Determining publish details")

        tank_type = output["tank_type"]
        
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]

        # Find additional info from the scene:

        progress_cb(10, "Analysing scene")

        progress_cb(30, "Exporting Maya Rig")
        
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        
        publish_path = publish_template.apply_fields(fields)
        publish_name = fields['Asset'] + '_maya_rig'

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)

        self.parent.ensure_folder_exists(publish_folder)
        
        oldsel = cmds.ls(sl=True)
        cmds.select(cl=True)

        cmds.select(item['name'])

        # export selected
        try:
            cmds.file(publish_path, typ='mayaAscii', pr=True, es=True)

        except Exception, e:
            raise TankError("Failed to export Alembic Cache: %s" % e)

        progress_cb(75, "Registering the publish")
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)

        cmds.select(cl=True)
        cmds.select(oldsel)


    def __publish_maya_surface(self, item, output, work_template, primary_publish_path,
                                        sg_task, comment, thumbnail_path, progress_cb):

        oldsel = cmds.ls(sl=True)
        cmds.select(cl=True)

        progress_cb(10, "Determining publish details")
        
        tank_type = output["tank_type"]
        
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]

        # Find additional info from the scene:

        progress_cb(10, "Analysing scene")

        progress_cb(30, "Exporting Maya Model")
        
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        
        publish_path = publish_template.apply_fields(fields)
        publish_name = fields['Asset'] + '_maya_surface'

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)

        self.parent.ensure_folder_exists(publish_folder)
                
        texture_template = self.parent.sgtk.templates['maya_surface_texture_publish_root']
        for file_node in item['file_nodes']:

            for texture_path in file_node['texture_paths']:
                texture_fname = texture_path.split('/')[-1]

                fields['channel'] = texture_fname.split('.')[0].split('_')[-1]
                try:
                    texture_root = texture_template.apply_fields(fields)
                except:
                    print 'Failed to match entity_channel.udim format. Saving to misc folder.'
                    fields['channel'] = 'misc'
                    texture_root = texture_template.apply_fields(fields)

                if not os.path.isdir(texture_root):
                    os.makedirs(texture_root)

                shutil.copyfile(texture_path, texture_root.replace('\\', '/') + '/' + texture_fname)

            new_fileTextureName = texture_root + '/' + file_node['fileTextureName'].split('/')[-1]
            file_node['old_fileTextureName'] = file_node['fileTextureName']
            cmds.setAttr('%s.%s' % (file_node['file_node'], 'fileTextureName'), new_fileTextureName, type='string')

        cmds.select(item['name'])
        
        # export selected
        try:
            cmds.file(publish_path, typ='mayaAscii', pr=True, es=True)
        except Exception, e:
            raise TankError("Failed to export Maya Surfacing Scene: %s" % e)

        progress_cb(75, "Registering the publish")
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)
        
        # restore old textures
        for file_node in item['file_nodes']:
            cmds.setAttr('%s.%s' % (file_node['file_node'], 'fileTextureName'), file_node['old_fileTextureName'], type='string')


    def __publish_maya_model(self, item, output, work_template, primary_publish_path,
                                        sg_task, comment, thumbnail_path, progress_cb):

        progress_cb(10, "Determining publish details")

        tank_type = output["tank_type"]
        
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]

        # Find additional info from the scene:

        progress_cb(10, "Analysing scene")

        progress_cb(30, "Exporting Maya Model")
        
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        
        publish_path = publish_template.apply_fields(fields)
        publish_name = fields['Asset'] + '_maya_model'

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)

        self.parent.ensure_folder_exists(publish_folder)
        
        #repath textures
        texture_root = os.path.join('\\'.join(publish_folder.split('\\')[0:-1]), 'textures', 'v'+ str(publish_version).zfill(3))
        
        texture_template = self.parent.sgtk.templates['maya_displacement_texture_publish_root']

        for i in item['vray_disp_nodes']:
            texture_nodes = i['texture_nodes']
            for texture_node in texture_nodes:
                for texture_path in texture_node['texture_paths']:
                    texture_fname = texture_path.split('/')[-1]
                    fields['channel'] = texture_fname.split('.')[0].split('_')[-1]                    
                    try:
                        texture_root = texture_template.apply_fields(fields)
                    except:
                        print 'Failed to match entity_channel.udim.ext format. Saving to misc folder.'
                        fields['channel'] = 'misc'
                        texture_root = texture_template.apply_fields(fields)

                    if not os.path.isdir(texture_root):
                        os.makedirs(texture_root)

                    shutil.copyfile(texture_path, texture_root.replace('\\', '/') + '/' + texture_fname)
                new_fileTextureName = texture_root + '/' + texture_node['fileTextureName'].split('/')[-1]
                texture_node['old_fileTextureName'] = texture_node['fileTextureName']
                cmds.setAttr('%s.%s' % (texture_node['file_node'], 'fileTextureName'), new_fileTextureName, type='string')

                
        print '===========selecting================='
        oldsel = cmds.ls(sl=True)
        cmds.select(cl=True)

        print 'selecting %s' % item['name']
        cmds.select(item['name'])
        for i in item['vray_disp_nodes']:
            print 'selecting %s' % i['vray_disp_node']
            cmds.select(i['vray_disp_node'], ne=True, add=True)

        # export selected
        try:
            cmds.file(publish_path, typ='mayaAscii', pr=True, es=True)

        except Exception, e:
            raise TankError("Failed to export Alembic Cache: %s" % e)

        progress_cb(75, "Registering the publish")
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)
        
        # restore old textures
        for i in item['vray_disp_nodes']:
            texture_nodes = i['texture_nodes']
            for texture_node in texture_nodes:
                texture_node['old_fileTextureName'] = texture_node['fileTextureName']
                cmds.setAttr('%s.%s' % (texture_node['file_node'], 'fileTextureName'), texture_node['old_fileTextureName'], type='string')


        cmds.select(cl=True)
        cmds.select(oldsel)


    def __publish_alembic_cache(self, item, output, work_template, primary_publish_path,
                                        sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish an Alembic cache file for the scene and publish it to Shotgun.

        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """
        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")
        import pprint 

        # Revilo - Add naming for use in alembic export
        tank_type = output["tank_type"]
        
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]

        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        progress_cb(30, "Exporting Alembic cache")
        caches = item['caches']


        for geo, data in caches.iteritems():
            alembic_args = ["-renderableOnly",   # only renderable objects (visible and not templated)
                        "-writeFaceSets",    # write shading group set assignments (Maya 2015+)
                        "-uvWrite",          # write uv's (only the current uv set gets written)
                        "-stripNamespaces",  # Revilo - Strip namespaces to ensure animation wrapping works
                        "-worldSpace"       # Revilo - Worldspace export
                        ]
            # find the animated frame range to use:
            start_frame, end_frame = self._find_scene_animation_range()
            if start_frame and end_frame:
                alembic_args.append("-fr %d %d" % (start_frame, end_frame))

            # Revilo - Add custom attributes to export string
            alembic_args.append("-attr uuid -attr alembic -attr subframe -attr version -attr artist -attr notes")
            fields = work_template.get_fields(scene_path)
            publish_version = fields["version"]
            publish_name = data['group_name']
            group_name = data['group_name']

            namespace = geo.split('|')[1].split(':')[0]
            geo_root = geo.split('|')[-1].split(':')[-1]

            fields["grp_name"] = namespace

            publish_path = publish_template.apply_fields(fields)

            # ensure the publish folder exists:
            publish_folder = os.path.dirname(publish_path)

            print 'publish path = %s' % publish_path
            self.parent.ensure_folder_exists(publish_folder)

            # update fields with the group name:
            
            if not publish_name:
                publish_name = os.path.basename(publish_path)
            
            geoItem = data["selection"]
            shutterAngle = data["shutterAngle"]
            alembic_args.append("-frs -%d" % (shutterAngle))
            alembic_args.append("-frs %d" % (shutterAngle))
            alembic_args.append("-root %s" % (geoItem))
            alembic_args.append("-file %s" % publish_path.replace("\\", "/").replace(':', '_'))

            abc_export_cmd = ("AbcExport -j \"%s\"" % " ".join(alembic_args))
            print abc_export_cmd
            try:
                self.parent.log_debug("Executing command: %s" % abc_export_cmd)
                mel.eval(abc_export_cmd)
            except Exception, e:
                raise TankError("Failed to export Alembic Cache: %s" % e)

        # register the publish:
        if 'Shot' in fields:
            publish_name = fields['Shot'] + '_' + fields['Step'] + '_alembic_caches'
        else:
            publish_name = fields['Step'] + '_alembic_caches'
        print publish_name
        publish_path = os.path.dirname(publish_path)
        progress_cb(75, "Registering the publish")
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        print args
        tank.util.register_publish(**args)

    # Added by: Chet
    # Date: 18/05/2018
    # Project: otherside

    # Added a secondary publish for geometry caches
    def __publish_geometry_cache(self, item, output, work_template, primary_publish_path,
                                        sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish an Alembic cache file for the scene and publish it to Shotgun.

        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """
        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")

        # Revilo - Add naming for use in alembic export
        #group_name = item["name"].strip("|")
        #meshes = item["meshes"]
        
        tank_type = output["tank_type"]
        publish_template = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]

        # update fields with the group name:
        #fields["grp_name"] = group_name

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # determine the publish name:
        publish_name = fields['Shot'] + '_' + fields['Step'] + item['name']

        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        # set the geometry cache arguments

        # find the animated frame range to use:
        start_frame, end_frame = self._find_scene_animation_range()

        # ...and execute it:

        progress_cb(30, "Exporting Geometry cache")
        caches = item['caches']
        for geo, meshes in caches.iteritems():
            group_name = geo.strip("|")
            try:
                self.parent.log_debug("Executing command: cacheFile")
                cmds.cacheFile(dir = publish_path.replace("\\", "/"), 
                            f= group_name, 
                            st=start_frame, 
                            et=end_frame, 
                            points=meshes,
                            cf='mcc',
                            worldSpace=True,
                            format='OneFile',
                            singleCache= True
                            )
            
            except Exception, e:
                raise TankError("Failed to export Geometry Cache: %s" % e)

        # register the publish:
        progress_cb(75, "Registering the publish")
        
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type,
        }

        tank.util.register_publish(**args)

    def _find_scene_animation_range(self):
        """
        Find the animation range from the current scene.
        """
        # look for any animation in the scene:
        animation_curves = cmds.ls(typ="animCurve")

        # if there aren't any animation curves then just return
        # a single frame:
        if not animation_curves:
            return (1, 1)

        # something in the scene is animated so return the
        # current timeline.  This could be extended if needed
        # to calculate the frame range of the animated curves.
        start = int(cmds.playbackOptions(q=True, min=True))
        end = int(cmds.playbackOptions(q=True, max=True))

        return (start, end)
# Tony added for publishing rendered images inside maya
    def __publish_rendered_images(self, item, output, work_template, primary_publish_path,
                                  sg_task, comment, thumbnail_path, progress_cb):
        """
         Publish rendered images and register with Shotgun.

         :param item:                    The item to publish
         :param output:                  The output definition to publish with
         :param work_template:           The work template for the current scene
         :param primary_publish_path:    The path to the primary published file
         :param sg_task:                 The Shotgun task we are publishing for
         :param comment:                 The publish comment/description
         :param thumbnail_path:          The path to the publish thumbnail
         :param progress_cb:             A callback that can be used to report progress
         """


         # determine the publish info to use
         #

        progress_cb(10, "Determining publish details")

        app = self.parent
        engine = tank.platform.current_engine()
        
        # get the current scene path and extract fields from it
        # using the work template:

        src_folder = os.path.split(item['other_params']['src_path'])[0]
        dst_folder = os.path.split(item['other_params']['dst_path'])[0]

        for i in os.listdir(src_folder):
            self.parent.copy_file(os.path.join(src_folder,i), os.path.join(dst_folder,i), sg_task)

        
        publish_path = item['other_params']['dst_path']
        publish_name = item['name']
        publish_version = item['version']
        tank_type = item['type']

        progress_cb(75, "Registering the publish")
        args = {
             "tk": self.parent.tank,
             "context": self.parent.context,
             "comment": comment,
             "path": publish_path,
             "name": publish_name,
             "version_number": publish_version,
             "thumbnail_path": thumbnail_path,
             "task": sg_task,
             "dependency_paths": [primary_publish_path],
             "published_file_type": tank_type
        }
        tank.util.register_publish(**args)

        # # Creating the path needed for copying
        # Temp_a = self.parent.sgtk.templates['shot_publish_area_maya']
        # toDirectory = Temp_a.apply_fields(fields).replace('\\','/')

        # Temp_a = self.parent.sgtk.templates['maya_shot_rendered_location']
        # toDirectoryC = Temp_a.apply_fields(fields).replace('\\','/')

        # Temp_b = self.parent.sgtk.templates['maya_shot_render_location']
        # fromDirectory = Temp_b.apply_fields(fields).replace('\\','/')


        # def getFiles(path):
        #     d,m,f=[],[],[]
        #     for (dirpath, dirnames, filenames) in walk(path):
        #         f.extend(filenames)
        #         d.append(dirpath)
        #     del d[0]
        #     for path in d:
        #         f,g=[path],[]
        #         for (dirpath, dirnames, filenames) in walk(path):
        #             g.extend(filenames)
        #         f.append(g)
        #         m.append(f)
        #     return (m)
        # # Creating Empty files to syc to shotgun (this will save ALOT of time)
        # def createEXRs(fileList):
        #     for folder in fileList:
        #         path = folder[0].split("/")
        #         path = toDirectory + "/" + path[-1] + "/" + path[0]
        #         if not os.path.exists(path):
        #             os.makedirs(path)
        #         for item in folder:
        #             if isinstance(item, list):
        #                 for z in item:
        #                     z = path + "/" + z
        #                     f= open(str(z),"w+")
        #                     f.close()    

        
        # import time
        # progress_cb(30, str(toDirectory))
        # imagesPath = fromDirectory
        # fileList = getFiles(imagesPath)
        # createEXRs(fileList)

        # # scan the publish folder for the empty exr we just made to get ready to publish them onto shotgun
        # progress_cb(30, str(fromDirectory))

        # determine the template for the publish path

        # get all the secondary output render templates and match them against
        # what is on disk
        # secondary_outputs = app.get_setting("secondary_outputs")
        # render_outputs = [out for out in secondary_outputs if out["tank_type"] == "Rendered Image"]
        # for render_output in render_outputs:

        #     render_template = self.parent.sgtk.templates['maya_shot_rendered']
 
        #     # iterate over all layers
        #     for layer in cmds.ls(type="renderLayer"):

        #             # apparently maya has 2 names for the default layer. I'm
        #             # guessing it actually renders out as 'masterLayer'.
        #             layer = layer.replace("defaultRenderLayer", "masterLayer")

        #             # these are the fields to populate into the template to match
        #             # against
        #             field = {
        #                 'maya.layer_name': layer,
        #                 'name': layer,
        #                 'version': version,
        #                 'Step': shotstep,
        #                 'Shot': shotn,
        #             }

        #             # match the files we just moved against the render template
        #             npaths = engine.tank.abstract_paths_from_template(
        #                 render_template, field)
        #             if npaths:
        #                 nitems.append(npaths[0])
                    

        # # setting the new published path of the renders in the publish directory

        # scene_name = cmds.file(q=True, sn=True)
        # fields = work_template.get_fields(scene_path)
        # work_template = app.get_template("template_work")
        # work_template_fields = work_template.get_fields(scene_name)
        
        # publish_version = fields["version"]
        # version = work_template_fields["version"]
        # shotstep = fields["Step"]
        # shotn = fields["Shot"]

        # #work_template = eng.get_template("template_work")
        # #work_template_fields = work_template.get_fields(scene_name)
        # render_template = self.parent.sgtk.templates["maya_shot_rendered"]

        # fields = {
        #     'Shot': shotn,
        #     'Step': shotstep,
        #     'Sequence': work_template_fields["Sequence"],
        #     'maya.layer_name': item['layer'],
        #     'version': version,
        #     'Seq':4
        # }

        # publish_name = item["name"]
        # publish_path = render_template.apply_fields(fields)

        # register the publish:
        # progress_cb(75, "Registering the publish")
        # args = {
        #      "tk": self.parent.tank,
        #      "context": self.parent.context,
        #      "comment": comment,
        #      "path": publish_path,
        #      "name": publish_name,
        #      "version_number": publish_version,
        #      "thumbnail_path": thumbnail_path,
        #      "task": sg_task,
        #      "dependency_paths": [primary_publish_path],
        #      "published_file_type": tank_type
        # }
        # tank.util.register_publish(**args)
        #copy the actual files over to replace the empty exr we just made
        # copy_tree(fromDirectory, toDirectoryC)



# Revilo - Logic for publishing the camera is added
    def __publish_camera(self, item, output, work_template,
        primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish a shot camera and register with Shotgun.

        :param item:           The item to publish
        :param output:         The output definition to publish with
        :param work_template:  The work template for the current scene
        :param primary_publish_path: The path to the primary published file
        :param sg_task:        The Shotgun task we are publishing for
        :param comment:        The publish comment/description
        :param thumbnail_path: The path to the publish thumbnail
        :param progress_cb:    A callback that can be used to report progress
        """

        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]
        cam_name = item['name']
        fields['obj_name'] = cam_name
        fields['name'] = re.sub(r'[\W_]+', '', cam_name)
        shutterAngle = item["shutterAngle"]

        # create the publish path by applying the fields
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields).split(".ma")[0] + ".abc"

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # determine the publish name
        publish_name = fields.get("obj_name")
        if not publish_name:
            publish_name = os.path.basename(publish_path)

        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        cmds.select(cam_name, replace=True)

        # Revilo - Replace .ma write with alembic export Logic
        # # write a .ma file to the publish path with the camera definitions
        # progress_cb(25, "Exporting the camera.")
        # cmds.file(publish_path, type='mayaAscii', exportSelected=True,
        #     options="v=0", prompt=False, force=True)


        # set the alembic args that make the most sense when working with Mari.  These flags
        # will ensure the export of an Alembic file that contains all visible geometry from
        # the current scene together with UV's and face sets for use in Mari.
        alembic_args = ["-renderableOnly",   # only renderable objects (visible and not templated)
                        "-writeFaceSets",    # write shading group set assignments (Maya 2015+)
                        "-uvWrite",          # write uv's (only the current uv set gets written)
                        #"-stripNamespaces",  # Revilo - Strip namespaces to ensure animation wrapping works
                        "-worldSpace",       # Revilo - Worldspace export
                        ]

        # find the animated frame range to use:
        start_frame, end_frame = self._find_scene_animation_range()
        if start_frame and end_frame:
            alembic_args.append("-fr %d %d" % (start_frame, end_frame))

        # Revilo - Add the subframe + and - values to the export
        alembic_args.append("-frs -%d" % (shutterAngle))
        alembic_args.append("-frs %d" % (shutterAngle))

        # Revilo - Add custom attributes to export string
        alembic_args.append("-attr uuid -attr alembic -attr subframe -attr version -attr artist -attr notes")

        # Revilo - Export only the selected camera
        alembic_args.append("-root %s" % (cam_name))

        # Set the output path:
        # Note: The AbcExport command expects forward slashes!
        alembic_args.append("-file %s" % publish_path.replace("\\", "/"))

        # build the export command.  Note, use AbcExport -help in Maya for
        # more detailed Alembic export help
        abc_export_cmd = ("AbcExport -j \"%s\"" % " ".join(alembic_args))

        # ...and execute it:
        progress_cb(30, "Exporting Alembic Camera")
        try:
            self.parent.log_debug("Executing command: %s" % abc_export_cmd)
            mel.eval(abc_export_cmd)
        except Exception, e:
            raise TankError("Failed to export Alembic Camera: %s" % e)

        # register the publish:
        progress_cb(75, "Registering the publish")
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type

        }
        tank.util.register_publish(**args)
