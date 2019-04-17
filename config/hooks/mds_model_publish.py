import maya.cmds as cmds
import pymel.core as pm
import os 
import re

def get_file_nodes(node):
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
        file_nodes = get_file_nodes(i)
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