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
    EnumProperty,
)


class OBJECT_OT_equalizerer(Operator):
    bl_idname = "object.equalizerer"
    bl_label = "Equalizerer"
    bl_description = "Use sound to turn a mesh into a part of an animated equalizer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def properties_changed(self):
        return (
            self.tmp_frequencyStart != self.frequencyStart or
            self.tmp_frequencyEnd != self.frequencyEnd or
            self.tmp_frequencyFraction != self.frequencyFraction or
            self.tmp_columnOffset != self.columnOffset or
            self.tmp_rowsCount != self.rowsCount or
            self.tmp_rowFramesOffset != self.rowFramesOffset or
            self.tmp_rowOffset != self.rowOffset or
            self.tmp_soundSequence != self.soundSequence or
            self.tmp_bakeSound != self.bakeSound
        )

    def update_properties(self):
        self.tmp_frequencyStart = self.frequencyStart
        self.tmp_frequencyEnd = self.frequencyEnd
        self.tmp_frequencyFraction = self.frequencyFraction
        self.tmp_columnOffset = self.columnOffset
        self.tmp_rowsCount = self.rowsCount
        self.tmp_rowFramesOffset = self.rowFramesOffset
        self.tmp_rowOffset = self.rowOffset
        self.tmp_soundSequence = self.soundSequence
        self.tmp_bakeSound = self.bakeSound

    tmp_frequencyStart = 0
    tmp_frequencyEnd = 0
    tmp_frequencyFraction = 0
    tmp_columnOffset = (0, 0, 0)
    tmp_rowsCount = 0
    tmp_rowFramesOffset = 0
    tmp_rowOffset = (0, 0, 0)
    tmp_soundSequence = ''
    tmp_bakeSound = False

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
        name = "Rows Offset",
        description = "Offset of the rows (cols)",
        default = (0, 1, 0),
        subtype = 'XYZ',
    )

    def sound_sequence_callback(self, context):
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        sound_sequences = []
        for sequence in scene.sequence_editor.sequences:
            if sequence.type != 'SOUND':
                continue
            sound_sequences.append((sequence.sound.name, sequence.sound.name, sequence.sound.filepath))
        return sound_sequences

    soundSequence: EnumProperty(
        name = "Sound sequence",
        description = "",
        items = sound_sequence_callback,
        default = None,
        options = {'ANIMATABLE'},
        update = None,
        get = None,
        set = None
    )

    bakeSound: BoolProperty(
        name = "Bake sound",
        description = "This will take some time, enable this after you are happy with the grid...",
        default = False
    )


    def invoke(self, context, event):
        self.bakeSound = False
        return self.execute(context)


    @classmethod
    def poll(cls, context):
        return context.object.select_get() and (context.object.type == 'MESH' or context.object.type == 'SURFACE')


    def execute(self, context):
        src_obj = context.selected_objects[0]
        scene = context.scene

        # if the no property was changed, do nothing
        if not self.properties_changed():
            return {'CANCELLED'}

        # update temp-props
        self.update_properties()

        # check if any animation is set to the source object
        any_animation = False
        has_animated_material = False
        if src_obj.animation_data and src_obj.animation_data.action != None:
            any_animation = True
        if src_obj.active_material:
            if src_obj.active_material.node_tree:
                if src_obj.active_material.node_tree.animation_data:
                    if src_obj.active_material.node_tree.animation_data.action:
                        any_animation = True
                        has_animated_material = True

        # create the sequence_editor if not present
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # select the soundstrip from sequence_editor
        has_sound = False
        sound_path = None
        sound_offset = 1
        for sequence in scene.sequence_editor.sequences:
            if sequence.type != 'SOUND':
                continue
            has_sound = True
            if self.soundSequence == sequence.sound.name:
                sound_path = bpy.path.abspath(sequence.sound.filepath)
                sound_offset = sequence.frame_start

        # Animation is missing
        if not any_animation:
            self.report({'ERROR'}, "At least one animation has to be set on the selected object")
            return {'CANCELLED'}

        # sound_path is missing
        if not has_sound:
            self.report({'ERROR'}, "Sound is missing, add a sound sequence to the Video Editor")
            return {'CANCELLED'}

        scene.frame_set(sound_offset)

        loopFreq = self.frequencyStart
        frequencies = []
        while True:
            if loopFreq > self.frequencyEnd:
                break
            frequencies.append(loopFreq)
            loopFreq = loopFreq + math.ceil(loopFreq / self.frequencyFraction)

        # loop all rows
        for h in range(self.rowsCount):
            scene.frame_set(sound_offset + h * self.rowFramesOffset)
            # loop all frequencies
            for f in range(len(frequencies)):
                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = src_obj
                src_obj.select_set(True)
                bpy.ops.object.duplicate()
                active = context.active_object

                # move the new object to the location in the grid
                active.location.x += (active.dimensions.x * self.columnOffset.x * f) + (active.dimensions.x * self.rowOffset.x * h)
                active.location.y += (active.dimensions.y * self.columnOffset.y * f) + (active.dimensions.y * self.rowOffset.y * h)
                active.location.z += (active.dimensions.z * self.columnOffset.z * f) + (active.dimensions.z * self.rowOffset.z * h)

                if self.bakeSound and sound_path:
                    # copy the material from source object
                    if has_animated_material:
                        active.active_material = src_obj.active_material.copy()
                        active.active_material.node_tree.animation_data.action = src_obj.active_material.node_tree.animation_data.action.copy()
                    # define the frquency to bake
                    lowF = frequencies[f]
                    highF = self.frequencyEnd if f+1 >= len(frequencies) else frequencies[f+1]
                    # select the object
                    bpy.ops.object.select_all(action='DESELECT')
                    active.select_set(True)
                    # switch to GRAPH_EDITOR
                    area = context.area
                    area_type = area.type
                    area.type = 'GRAPH_EDITOR'
                    # bake the sound
                    bpy.ops.anim.channels_select_all(action='SELECT')
                    bpy.ops.graph.sound_bake(filepath=sound_path, low=lowF, high=highF)
                    area.type = area_type

        # back to frame 1
        scene.frame_set(sound_offset)

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
