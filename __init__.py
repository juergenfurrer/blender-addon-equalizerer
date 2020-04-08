bl_info = {
    "name": "Equalizerer",
    "author": "Juergen Furrer",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Object",
    "description": "Use sound to turn a mesh into a part of an animated equalizer",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}


import math
import bpy
from bpy.types import (
    AddonPreferences,
    Operator,
    Panel,
    PropertyGroup
)
from bpy.props import (
    BoolProperty,
    FloatVectorProperty,
    IntProperty,
    FloatProperty,
    StringProperty,
)


class OBJECT_OT_equalizerer(Operator):
    bl_idname = "object.equalizerer"
    bl_label = "Equalizerer"
    bl_description = "Use sound to turn a mesh into a part of an animated equalizer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'REGISTER', 'UNDO'}


    frequencyStart: IntProperty(
        name = "Frequency Start",
        description = "Start of frequency",
        default = 20,
        min = 0,
        max = 20000,
    )

    frequencyEnd: IntProperty(
        name = "Frequency End",
        description = "End of frequency",
        default = 20000,
        min = 0,
        max = 20000,
    )

    frequencyFraction: FloatProperty(
        name = "Bar Fraction",
        description = "Frequency fraction to us (previous frequency-diff * 2 + frequency-diff * fraction)",
        default = 4,
        min = .1,
        max = 20,
    )

    columnOffset: FloatVectorProperty(
        name = "Bars Offset",
        description = "Offset of the bars (cols)",
        default = (1, 0, 0),
        subtype = 'XYZ',
    )

    rowsCount: IntProperty(
        name = "Row Count",
        description = "Rows to use (will take some times)",
        default = 1,
        min = 1,
        max = 100,
    )

    rowFramesOffset: IntProperty(
        name = "Row offset in frames",
        description = "Offset in frames for every row",
        default = 1,
        min = 0,
        max = 600,
    )

    rowOffset: FloatVectorProperty(
        name = "Bars Offset",
        description = "Offset of the bars (cols)",
        default = (0, 1, 0),
        subtype = 'XYZ',
    )

    bakeSound: BoolProperty(
        name = "Bake sound",
        description = "This will take some time, enable this after you are happy with the grid...",
        default = False
    )

    @classmethod
    def poll(cls, context):
        return context.object.select_get() and (context.object.type == 'MESH' or context.object.type == 'SURFACE')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def execute(self, context):
        src_obj = bpy.context.selected_objects[0]

        scene = bpy.context.scene
        scene.frame_set(1)

        # check if any animation is set to the source object
        any_animation = False
        if [getattr(src_obj.data, 'shape_keys', None)]:
            any_animation = True
        if src_obj.active_material and src_obj.active_material.node_tree.animation_data.action:
            any_animation = True

        # create the sequence_editor if not present
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # select the soundstrip from sequence_editor
        for sequence in scene.sequence_editor.sequences:
            if sequence.type != 'SOUND':
                continue
            sound_path = sequence.sound.filepath

        # Animation is missing
        if not any_animation:
            self.report({'ERROR'}, "At least one animation has to be set on the selected object")
            return {'CANCELLED'}

        # sound_path is missing
        if not sound_path:
            self.report({'ERROR'}, "Sound is missing, add a sound sequence to the Video Editor")
            return {'CANCELLED'}

        loopFreq = self.frequencyStart
        frequencies = []
        while True:
            if loopFreq > self.frequencyEnd:
                break
            frequencies.append(loopFreq)
            loopFreq = loopFreq + math.ceil(loopFreq / self.frequencyFraction)

        # loop all rows
        for h in range(self.rowsCount):
            scene.frame_set(1 + h * self.rowFramesOffset)
            # loop all frequencies
            for f in range(len(frequencies)):
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = src_obj
                src_obj.select_set(True)
                bpy.ops.object.duplicate()
                active = bpy.context.active_object

                # move the new object to the location in the grid
                active.location.x = (active.dimensions.x * self.columnOffset.x * f) + (active.dimensions.x * self.rowOffset.x * h)
                active.location.y = (active.dimensions.y * self.columnOffset.y * f) + (active.dimensions.y * self.rowOffset.y * h)
                active.location.z = (active.dimensions.z * self.columnOffset.z * f) + (active.dimensions.z * self.rowOffset.z * h)

                if self.bakeSound and sound_path:
                    # copy the material from source object
                    if src_obj.active_material and src_obj.active_material.node_tree.animation_data.action:
                        active.active_material = src_obj.active_material.copy()
                        active.active_material.node_tree.animation_data.action = src_obj.active_material.node_tree.animation_data.action.copy()
                    # define the frquency to bake
                    lowF = frequencies[f]
                    highF = self.frequencyEnd if f+1 >= len(frequencies) else frequencies[f+1]
                    # select the object
                    bpy.ops.object.select_all(action='DESELECT')
                    active.select_set(True)
                    # switch to GRAPH_EDITOR
                    area = bpy.context.area
                    area_type = area.type
                    area.type = 'GRAPH_EDITOR'
                    # bake the sound
                    bpy.ops.anim.channels_select_all(action='SELECT')
                    bpy.ops.graph.sound_bake(filepath=sound_path, low=lowF, high=highF)
                    area.type = area_type

        # back to frame 1
        scene.frame_set(1)

        # TODO: Hide the original, the hide_viewport is not unhidable?!?
        #src_obj.hide_viewport = True

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_equalizerer.bl_idname)


def register():
    bpy.utils.register_class(OBJECT_OT_equalizerer)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_equalizerer)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
