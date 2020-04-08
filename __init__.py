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

    offset: FloatVectorProperty(
        name = "Bars Offset",
        description = "Offset of the bars (cols)",
        default = (1, 0, 0),
        subtype = 'XYZ',
    )

    historyRowsCount: IntProperty(
        name = "Row Count",
        description = "Rows to use (will take some times)",
        default = 1,
        min = 1,
        max = 100,
    )

    historyFramesOffset: IntProperty(
        name = "Row offset in frames",
        description = "Offset in frames for every row",
        default = 1,
        min = 0,
        max = 600,
    )

    offsetHistory: FloatVectorProperty(
        name = "Bars Offset",
        description = "Offset of the bars (cols)",
        default = (0, 1, 0),
        subtype = 'XYZ',
    )

    soundPath: StringProperty(
        name = "Sound Path",
        description = "Sound to use for the equalizerer, first define the size, set this value at the end!",
        subtype = 'FILE_PATH',
    )


    @classmethod
    def poll(cls, context):
        return context.object.select_get() and (context.object.type == 'MESH' or context.object.type == 'SURFACE')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def execute(self, context):
        scene = bpy.context.scene
        src_obj = bpy.context.selected_objects[0]

        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # Define Sound and add it...
        sound = self.soundPath
        if sound:
            soundstrip = scene.sequence_editor.sequences.new_sound("sound", sound, 3, 1)
            scene.frame_end = soundstrip.frame_duration
        scene.frame_set(1)

        frequencyStart = self.frequencyStart
        frequencyEnd = self.frequencyEnd
        frequencyFraction = self.frequencyFraction

        offsetX = self.offset.x
        offsetY = self.offset.y
        offsetZ = self.offset.z

        historyFramesOffset = self.historyFramesOffset
        historyRowsCount = self.historyRowsCount
        historyX = self.offsetHistory.x
        historyY = self.offsetHistory.y
        historyZ = self.offsetHistory.z

        loopFreq = frequencyStart
        frequencies = []
        while True:
            if loopFreq > frequencyEnd:
                break
            frequencies.append(loopFreq)
            loopFreq = loopFreq + math.ceil(loopFreq / frequencyFraction)

        for h in range(historyRowsCount):
            scene.frame_set(1 + h * historyFramesOffset)
            for f in range(len(frequencies)):
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = src_obj
                src_obj.select_set(True)
                bpy.ops.object.duplicate()
                active = bpy.context.active_object
                # move to the 
                active.location.x = (active.dimensions.x * offsetX * f) + (active.dimensions.x * historyX * h)
                active.location.y = (active.dimensions.y * offsetY * f) + (active.dimensions.y * historyY * h)
                active.location.z = (active.dimensions.z * offsetZ * f) + (active.dimensions.z * historyZ * h)
                if sound:
                    # define the frquency to bake
                    lowF = frequencies[f]
                    highF = frequencyEnd if f+1 >= len(frequencies) else frequencies[f+1]
                    # select the object
                    bpy.ops.object.select_all(action='DESELECT')
                    active.select_set(True) 
                    area = bpy.context.area
                    area_type = area.type
                    area.type = 'GRAPH_EDITOR'
                    bpy.ops.anim.channels_select_all(action='SELECT')
                    bpy.ops.graph.sound_bake(filepath=sound, low=lowF, high=highF)
                    area.type = area_type

        scene.frame_set(1)
        #src_obj.hide_viewport = True

        return {'FINISHED'}


# Registration

def menu_func(self, context):
    self.layout.operator(
        OBJECT_OT_equalizerer.bl_idname)


def register():
    bpy.utils.register_class(OBJECT_OT_equalizerer)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_equalizerer)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
