# Puente entre las bibliotecas CC0 descargadas (herramientas/recursos.py) y las escenas de Blender.
# Una escena no vuelve a cargar texturas a mano: pide `mat_acg("Marble012")` y ya.
#
# Carpetas que espera (las crea el descargador):
#   recursos/ambientcg/<Id>/<Id>_2K-JPG_Color.jpg | _NormalGL.jpg | _Roughness.jpg | _Metalness.jpg | _Displacement.jpg
#   recursos/polyhaven/texturas/<id>/<id>_diffuse.jpg | _nor_gl.jpg | _arm.jpg | _rough.jpg | _ao.jpg
#   recursos/polyhaven/hdri/<id>_2k.hdr
#   recursos/polyhaven/<id>_2k.blend  (+ ./textures/ al lado)
import os
import math
import bpy
bpy.context.preferences.view.use_translate_new_dataname = False   # Blender en español nombra los nodos traducidos y rompe nodes["Principled BSDF"]

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recursos"))
_cache = {}


def _nodo_img(nt, ruta, mapeo, no_color=False):
    if not os.path.exists(ruta):
        return None
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(ruta, check_existing=True)
    if no_color:
        n.image.colorspace_settings.name = "Non-Color"
    nt.links.new(mapeo.outputs["Vector"], n.inputs["Vector"])
    return n


def _base(nombre, escala, escala_y=None):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Scale"].default_value = (escala, escala_y if escala_y else escala, escala)
    nt.links.new(coord.outputs["UV"], mapeo.inputs["Vector"])
    return m, nt, p, mapeo


def mat_acg(ident, escala=1.0, escala_y=None, res="2K-JPG", desplazar=0.0):
    """material de ambientCG: Color + NormalGL + Roughness (+ Metalness y Displacement si los trae)"""
    clave = ("acg", ident, escala, escala_y, desplazar)
    if clave in _cache:
        return _cache[clave]
    carpeta = os.path.join(RAIZ, "ambientcg", ident)
    m, nt, p, mapeo = _base(f"acg_{ident}", escala, escala_y)
    # unos se bajaron en JPG y otros en PNG: se usa el que exista
    ext = ".jpg"
    for r, e in ((res, ".jpg"), ("2K-PNG", ".png"), ("2K-JPG", ".jpg")):
        if os.path.exists(os.path.join(carpeta, f"{ident}_{r}_Color{e}")):
            res, ext = r, e
            break
    pre = os.path.join(carpeta, f"{ident}_{res}")
    col = _nodo_img(nt, pre + "_Color" + ext, mapeo)
    if col:
        nt.links.new(col.outputs["Color"], p.inputs["Base Color"])
    nor = _nodo_img(nt, pre + "_NormalGL" + ext, mapeo, True)
    if nor:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    rug = _nodo_img(nt, pre + "_Roughness" + ext, mapeo, True)
    if rug:
        nt.links.new(rug.outputs["Color"], p.inputs["Roughness"])
    met = _nodo_img(nt, pre + "_Metalness" + ext, mapeo, True)
    if met:
        nt.links.new(met.outputs["Color"], p.inputs["Metallic"])
    if desplazar:
        dsp = _nodo_img(nt, pre + "_Displacement" + ext, mapeo, True)
        if dsp:
            d = nt.nodes.new("ShaderNodeDisplacement")
            d.inputs["Scale"].default_value = desplazar
            nt.links.new(dsp.outputs["Color"], d.inputs["Height"])
            nt.links.new(d.outputs["Displacement"], nt.nodes["Material Output"].inputs["Displacement"])
            m.displacement_method = "BOTH"
    _cache[clave] = m
    return m


def mat_ph(ident, escala=1.0, escala_y=None):
    """material de Poly Haven: diffuse + nor_gl + arm (R=oclusión, G=rugosidad, B=metal)"""
    clave = ("ph", ident, escala, escala_y)
    if clave in _cache:
        return _cache[clave]
    carpeta = os.path.join(RAIZ, "polyhaven", "texturas", ident)
    m, nt, p, mapeo = _base(f"ph_{ident}", escala, escala_y)
    col = _nodo_img(nt, os.path.join(carpeta, f"{ident}_diffuse.jpg"), mapeo)
    if col:
        nt.links.new(col.outputs["Color"], p.inputs["Base Color"])
    nor = _nodo_img(nt, os.path.join(carpeta, f"{ident}_nor_gl.jpg"), mapeo, True)
    if nor:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    arm = _nodo_img(nt, os.path.join(carpeta, f"{ident}_arm.jpg"), mapeo, True)
    if arm:
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(arm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    else:
        rug = _nodo_img(nt, os.path.join(carpeta, f"{ident}_rough.jpg"), mapeo, True)
        if rug:
            nt.links.new(rug.outputs["Color"], p.inputs["Roughness"])
    _cache[clave] = m
    return m


def cielo_ph(escena, ident, res="2k", giro=0.0, fuerza=1.0):
    """pone un cielo HDRI real como iluminación del mundo"""
    mundo = bpy.data.worlds.new("cielo")
    escena.world = mundo
    mundo.use_nodes = True
    nt = mundo.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    salida = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None) or nt.nodes.new("ShaderNodeOutputWorld")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(RAIZ, "polyhaven", "hdri", f"{ident}_{res}.hdr"))
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Rotation"].default_value = (0, 0, math.radians(giro))
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Generated"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], env.inputs["Vector"])
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(env.outputs["Color"], fondo.inputs["Color"])
    nt.links.new(fondo.outputs["Background"], salida.inputs["Surface"])
    return mundo


def modelo_ph(ident, res="1k", coleccion=None):
    """trae un modelo fotoescaneado desde su .blend (devuelve los objetos nuevos)"""
    ruta = os.path.join(RAIZ, "polyhaven", f"{ident}_{res}.blend")
    nombre = coleccion or f"{ident}_LOD0"
    antes = set(bpy.context.scene.objects)
    bpy.ops.wm.append(filepath=os.path.join(ruta, "Collection", nombre),
                      directory=os.path.join(ruta, "Collection"), filename=nombre)
    return [o for o in bpy.context.scene.objects if o not in antes]


def gpu(escena, muestras=64, denoise=True):
    """Cycles con OptiX sobre la RTX; lo mismo en todas las escenas"""
    escena.render.engine = "CYCLES"
    escena.cycles.device = "GPU"
    escena.cycles.samples = muestras
    escena.cycles.use_denoising = denoise
    escena.cycles.denoiser = "OPTIX"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == "OPTIX")
    return [d.name for d in prefs.devices if d.use]
