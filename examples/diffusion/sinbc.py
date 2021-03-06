r"""
Laplace equation with boundary conditions given by sine functions.

Find :math:`t` such that:

.. math::
    \int_{\Omega} c \nabla s \cdot \nabla t
    = 0
    \;, \quad \forall s \;.
"""
from sfepy import data_dir

filename_mesh = data_dir + '/meshes/various_formats/comsol_tri.txt'

material_1 = {
    'name' : 'm',
    'values' : {'val' : 1.0},
}

region_1000 = {
    'name' : 'Omega',
    'select' : 'all',
}
region_3 = {
    'name' : 'Gamma_Bottom',
    'select' : 'nodes in (y < 0.00001)',
}
region_4 = {
    'name' : 'Gamma_Top',
    'select' : 'nodes in (y > 0.59999)',
}

field_1 = {
    'name' : 'temperature',
    'dtype' : 'real',
    'shape' : (1,),
    'region' : 'Omega',
    'approx_order' : 2,
}

variable_1 = {
    'name' : 't',
    'kind' : 'unknown field',
    'field' : 'temperature',
    'order' : 0,
}
variable_2 = {
    'name' : 's',
    'kind' : 'test field',
    'field' : 'temperature',
    'dual' : 't',
}

ebc_1 = {
    'name' : 't1',
    'region' : 'Gamma_Top',
    'dofs' : {'t.0' : 'ebc_sin'},
}
ebc_2 = {
    'name' : 't2',
    'region' : 'Gamma_Bottom',
    'dofs' : {'t.0' : 'ebc_sin2'},
}

integral_1 = {
    'name' : 'i1',
    'kind' : 'v',
    'quadrature' : 'gauss_o2_d2',
}

equations = {
    'Temperature' : """dw_laplace.i1.Omega( m.val, s, t )
                       = 0"""
}

solver_0 = {
    'name' : 'ls',
    'kind' : 'ls.scipy_direct',
}

solver_1 = {
    'name' : 'newton',
    'kind' : 'nls.newton',

    'i_max'      : 1,
    'eps_a'      : 1e-10,
    'eps_r'      : 1.0,
    'macheps'   : 1e-16,
    'lin_red'    : 1e-2, # Linear system error < (eps_a * lin_red).
    'ls_red'     : 0.1,
    'ls_red_warp' : 0.001,
    'ls_on'      : 1.1,
    'ls_min'     : 1e-5,
    'check'     : 0,
    'delta'     : 1e-6,
    'is_plot'    : False,
    'problem'   : 'nonlinear', # 'nonlinear' or 'linear' (ignore i_max)
}

options = {
    'nls' : 'newton',
    'ls' : 'ls',

    # Options for saving higher-order variables.
    # Possible kinds:
    #    'strip' ... just remove extra DOFs (ignores other linearization
    #                options)
    #    'adaptive' ... adaptively refine linear element mesh.
    'linearization' : {
        'kind' : 'strip',
        'min_level' : 0, # Min. refinement level to achieve everywhere.
        'max_level' : 3, # Max. refinement level.
        'eps' : 1e-2, # Relative error tolerance.
    },
    'output_format' : 'vtk',
}

import numpy as nm

amplitude = 2.0
def ebc_sin(ts, coor, **kwargs):
    x0 = 0.5 * (coor[:,0].min() + coor[:,0].max())
    val = amplitude * nm.sin( (coor[:,0] - x0) * 2. * nm.pi )
    return val

def ebc_sin2(ts, coor, **kwargs):
    x0 = 0.5 * (coor[:,0].min() + coor[:,0].max())
    val = amplitude * nm.sin( (coor[:,0] - x0) * 3. * nm.pi )
    return val

functions = {
    'ebc_sin' : (ebc_sin,),
    'ebc_sin2' : (ebc_sin2,),
}
