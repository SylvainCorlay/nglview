# adpated from Jupyter ipywidgets project.

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import nose.tools as nt
import gzip
import unittest
from numpy.testing import assert_equal as eq, assert_almost_equal as aa_eq
import numpy as np

from ipykernel.comm import Comm
import ipywidgets as widgets

from traitlets import TraitError
from ipywidgets import Widget


import pytraj as pt
import nglview as nv
from nglview import NGLWidget
import mdtraj as md
import parmed as pmd
# wait until MDAnalysis supports PY3
from nglview.utils import PY2, PY3


#-----------------------------------------------------------------------------
# Utility stuff from ipywidgets tests
#-----------------------------------------------------------------------------

class DummyComm(Comm):
    comm_id = 'a-b-c-d'

    def open(self, *args, **kwargs):
        pass

    def send(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

_widget_attrs = {}
displayed = []
undefined = object()

def setup():
    _widget_attrs['_comm_default'] = getattr(Widget, '_comm_default', undefined)
    Widget._comm_default = lambda self: DummyComm()
    _widget_attrs['_ipython_display_'] = Widget._ipython_display_
    def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError()
    Widget._ipython_display_ = raise_not_implemented


def teardown():
    for attr, value in _widget_attrs.items():
        if value is undefined:
            delattr(Widget, attr)
        else:
            setattr(Widget, attr, value)

#-----------------------------------------------------------------------------
# NGLView stuff
#-----------------------------------------------------------------------------

DEFAULT_REPR = [{'params': {'sele': 'polymer'}, 'type': 'cartoon'},
                {'params': {'sele': 'hetero OR mol'}, 'type': 'ball+stick'},
                {"type": "ball+stick", "params": {"sele": "not protein and not nucleic"}}
                ]

def _assert_dict_list_equal(listdict0, listdict1):
    for (dict0, dict1) in zip(listdict0, listdict1):
        for (key0, key1) in zip(sorted(dict0.keys()), sorted(dict1.keys())):
            nt.assert_equal(key0, key1)
            nt.assert_equal(dict0.get(key0), dict1.get(key1))

def test_API_promise_to_have():

    # Structure
    structure = nv.Structure()
    structure.get_structure_string
    nt.assert_true(hasattr(structure, 'id'))
    nt.assert_true(hasattr(structure, 'ext'))
    nt.assert_true(hasattr(structure, 'params'))

    # Widget
    nv.NGLWidget._set_coordinates
    nv.NGLWidget._set_initial_structure

    nv.NGLWidget.add_component
    nv.NGLWidget.add_trajectory
    nv.NGLWidget.coordinates_dict
    nv.NGLWidget.set_representations
    nv.NGLWidget.clear
    nv.NGLWidget.center

def test_coordinates_dict():
    traj = pt.load(nv.datafiles.TRR, nv.datafiles.PDB)
    view = nv.show_pytraj(traj)
    view.frame = 1
    coords = view.coordinates_dict[0]
    aa_eq(coords, traj[1].xyz)

def test_load_data():
    view = nv.show_pytraj(pt.datafiles.load_tz2())

    # load blob with ext
    blob = open(nv.datafiles.PDB).read()
    view._load_data(blob, ext='pdb')

    # raise if passing blob but does not provide ext
    nt.assert_raises(ValueError, view._load_data, blob)

    # load PyTrajectory
    t0 = nv.PyTrajTrajectory(pt.datafiles.load_ala3())
    view._load_data(t0)

    # load current folder
    # if run nosetests in nglview root folder, the path is not correct
    # turn of for now
    # view._load_data('data/tz2.pdb')


def test_representations():
    view = nv.show_pytraj(pt.datafiles.load_tz2())
    nt.assert_equal(view.representations, DEFAULT_REPR)
    view.add_cartoon()
    representations_2 = DEFAULT_REPR[:]
    representations_2.append({'type': 'cartoon', 'params': {'sele': 'all'}})
    print(representations_2)
    print(view.representations)
    _assert_dict_list_equal(view.representations, representations_2)
                    
def test_add_repr_shortcut():
    view = nv.show_pytraj(pt.datafiles.load_tz2())
    assert isinstance(view, nv.NGLWidget), 'must be instance of NGLWidget'
    view.add_cartoon(color='residueindex')
    view.add_rope(color='red')

def test_remote_call():
    # how to test JS?
    view = nv.show_pytraj(pt.datafiles.load_tz2())
    view._remote_call('centerView', target='stage')

    fn = 'notebooks/tz2.pdb'
    kwargs = {'defaultRepresentation': True}
    view._remote_call('loadFile', target='stage', args=[fn,], kwargs=kwargs)

def test_download_image():
    """just make sure it can be called
    """
    view = nv.show_pytraj(pt.datafiles.load_tz2())
    view.download_image('myname.png', 2, False, False, True)

def test_show_structure_file():
    view = nv.show_structure_file(nv.datafiles.PDB)

def test_show_simpletraj():
    traj = nv.SimpletrajTrajectory(nv.datafiles.XTC, nv.datafiles.GRO)
    view = nv.show_simpletraj(traj)
    view

def test_show_mdtraj():
    import mdtraj as md
    from mdtraj.testing import get_fn
    fn = nv.datafiles.PDB 
    traj = md.load(fn)
    view = nv.show_mdtraj(traj)

def test_show_MDAnalysis():
    from MDAnalysis import Universe
    tn, fn = nv.datafiles.PDB, nv.datafiles.PDB
    u = Universe(fn, tn)
    view = nv.show_mdanalysis(u)

def test_show_parmed():
    import parmed as pmd
    fn = nv.datafiles.PDB 
    parm = pmd.load_file(fn)
    view = nv.show_parmed(parm)

def test_encode_and_decode():
    xyz = np.arange(100).astype('f4')
    shape = xyz.shape

    b64_str = nv.encode_base64(xyz)
    new_xyz = nv.decode_base64(b64_str, dtype='f4', shape=shape)
    aa_eq(xyz, new_xyz) 

def test_coordinates_meta():
    from mdtraj.testing import get_fn
    fn, tn = [get_fn('frame0.pdb'),] * 2
    trajs = [pt.load(fn, tn), md.load(fn, top=tn), pmd.load_file(tn, fn)]

    N_FRAMES = trajs[0].n_frames

    from MDAnalysis import Universe
    u = Universe(tn, fn)
    trajs.append(Universe(tn, fn))

    views = [nv.show_pytraj(trajs[0]), nv.show_mdtraj(trajs[1]), nv.show_parmed(trajs[2])]
    views.append(nv.show_mdanalysis(trajs[3]))

    for index, (view, traj) in enumerate(zip(views, trajs)):
        view.frame = 3
        
        nt.assert_equal(view._trajlist[0].n_frames, N_FRAMES)

def test_structure_file():
    for fn in ['data/tz2.pdb', nv.datafiles.GRO]:
        content = open(fn, 'rb').read()
        fs1 = nv.FileStructure(fn)
        nt.assert_equal(content, fs1.get_structure_string()) 
    
    # gz
    fn = 'data/tz2_2.pdb.gz'
    fs2 = nv.FileStructure(fn)
    content = gzip.open(fn).read()
    nt.assert_equal(content, fs2.get_structure_string()) 

def test_camelize_parameters():
    view = nv.NGLWidget()
    view.parameters = dict(background_color='black')
    nt.assert_true('backgroundColor' in view._parameters) 

def test_component_for_duck_typing():
    view = NGLWidget()
    view.add_component('data/tz2.pdb')
    view.add_component('data/tz2_2.pdb.gz')
    
    c0 = view[0]
    c1 = view[1]
    nt.assert_true(hasattr(view, 'component_0'))
    nt.assert_true(hasattr(view, 'component_1'))

    c0.show()
    c0.hide()

    view.remove_component(c0.id)
    nt.assert_false(hasattr(view, 'component_1'))

def test_trajectory_show_hide_sending_cooridnates():
    view = NGLWidget()

    traj0 = pt.datafiles.load_tz2()
    traj1 = pt.datafiles.load_trpcage()

    view.add_trajectory(nv.PyTrajTrajectory(traj0))
    view.add_trajectory(nv.PyTrajTrajectory(traj1))

    for traj in view._trajlist:
        nt.assert_true(traj.shown)

    view.frame = 1

    def copy_coordinate_dict(view):
        # make copy to avoid memory free
        return dict((k, v.copy()) for k, v in view.coordinates_dict.items())

    coordinates_dict = copy_coordinate_dict(view)
    aa_eq(coordinates_dict[0], traj0[1].xyz) 
    aa_eq(coordinates_dict[1], traj1[1].xyz) 

    # hide 0
    view.hide([0,])
    nt.assert_false(view._trajlist[0].shown)
    nt.assert_true(view._trajlist[1].shown)

    # update frame so view can update its coordinates
    view.frame = 2
    coordinates_dict = copy_coordinate_dict(view)
    nt.assert_equal(coordinates_dict[0].shape[0], 0)
    aa_eq(coordinates_dict[1], traj1[2].xyz)

    # hide 0, 1
    view.hide([0, 1])
    nt.assert_false(view._trajlist[0].shown)
    nt.assert_false(view._trajlist[1].shown)
    view.frame = 3
    coordinates_dict = copy_coordinate_dict(view)
    nt.assert_equal(coordinates_dict[0].shape[0], 0)
    nt.assert_equal(coordinates_dict[1].shape[0], 0)

    # slicing, show only component 1
    view[1].show()
    view.frame = 0
    nt.assert_false(view._trajlist[0].shown)
    nt.assert_true(view._trajlist[1].shown)
    coordinates_dict = copy_coordinate_dict(view)
    nt.assert_equal(coordinates_dict[0].shape[0], 0)
    aa_eq(coordinates_dict[1], traj1[0].xyz)

    # show all
    view[1].show()
    view[0].show()
    view.frame = 1
    nt.assert_true(view._trajlist[0].shown)
    nt.assert_true(view._trajlist[1].shown)
    coordinates_dict = copy_coordinate_dict(view)
    aa_eq(coordinates_dict[0], traj0[1].xyz)
    aa_eq(coordinates_dict[1], traj1[1].xyz)

    # hide all
    view[1].hide()
    view[0].hide()
    view.frame = 2
    nt.assert_false(view._trajlist[0].shown)
    nt.assert_false(view._trajlist[1].shown)
    coordinates_dict = copy_coordinate_dict(view)
    nt.assert_equal(coordinates_dict[0].shape[0], 0)
    nt.assert_equal(coordinates_dict[1].shape[0], 0)
