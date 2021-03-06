import numpy as nm

from sfepy.base.base import use_method_with_name
from sfepy.terms.terms import Term, terms
from sfepy.terms.terms_base import CouplingVectorScalar, CouplingVectorScalarTH
from sfepy.terms.termsLinElasticity import CauchyStrainTerm

class BiotTerm(Term):
    r"""
    :Description:
    Biot coupling term with :math:`\alpha_{ij}`
    given in vector form exploiting symmetry: in 3D it has the
    indices ordered as :math:`[11, 22, 33, 12, 13, 23]`, in 2D it has
    the indices ordered as :math:`[11, 22, 12]`. Corresponds to weak
    forms of Biot gradient and divergence terms. Can be evaluated. Can
    use derivatives.

    :Definition:
    .. math::
        \int_{\Omega}  p\ \alpha_{ij} e_{ij}(\ul{v}) \mbox{ , } \int_{\Omega}
        q\ \alpha_{ij} e_{ij}(\ul{u})

    :Arguments 1:
        material : :math:`\alpha_{ij}`,
        virtual  : :math:`\ul{v}`,
        state    : :math:`p`

    :Arguments 2:
        material : :math:`\alpha_{ij}`,
        state    : :math:`\ul{u}`,
        virtual  : :math:`q`

    :Arguments 3:
        material    : :math:`\alpha_{ij}`,
        parameter_v : :math:`\ul{u}`,
        parameter_s : :math:`p`
    """
    name = 'dw_biot'
    arg_types = (('material', 'virtual', 'state'),
                 ('material', 'state', 'virtual'),
                 ('material', 'parameter_v', 'parameter_s'))
    modes = ('grad', 'div', 'eval')

    def get_fargs(self, mat, vvar, svar,
                  mode=None, term_mode=None, diff_var=None, **kwargs):
        if self.mode == 'grad':
            qp_var, qp_name = svar, 'val'

        else:
            qp_var, qp_name = vvar, 'cauchy_strain'

        if mode == 'weak':
            vvg, _ = self.get_mapping(vvar)
            svg, _ = self.get_mapping(svar)

            if diff_var is None:
                val_qp = self.get(qp_var, qp_name)
                fmode = 0

            else:
                val_qp = nm.array([0], ndmin=4, dtype=nm.float64)
                fmode = 1

            return 1.0, val_qp, svg.bf, mat, vvg, fmode

        elif mode == 'eval':
            vvg, _ = self.get_mapping(vvar)

            strain = self.get(vvar, 'cauchy_strain')
            pval = self.get(svar, 'val')

            return 1.0, pval, strain, mat, vvg

        else:
            raise ValueError('unsupported evaluation mode in %s! (%s)'
                             % (self.name, mode))

    def get_eval_shape(self, mat, vvar, svar,
                       mode=None, term_mode=None, diff_var=None, **kwargs):
        n_el, n_qp, dim, n_en, n_c = self.get_data_shape(vvar)

        return (n_el, 1, 1, 1), vvar.dtype

    def set_arg_types(self):
        self.function = {
            'grad' : terms.dw_biot_grad,
            'div' : terms.dw_biot_div,
            'eval' : terms.d_biot_div,
        }[self.mode]

class BiotStressTerm(CauchyStrainTerm):
    r"""
    :Description:
    Biot stress tensor averaged in elements.
    
    :Definition:
    .. math::
        \mbox{vector for } K \from \Ical_h:
        \int_{T_K} \alpha_{ij} \bar{p} / \int_{T_K} 1

    :Arguments:
        material  : :math:`\alpha_{ij}`,
        parameter : :math:`\bar{p}`
    """
    name = 'de_biot_stress'
    arg_types = ('material', 'parameter')
    use_caches = {'state_in_volume_qp' : [['parameter']]}

    function = staticmethod(terms.de_cauchy_stress)

    def build_c_fun_args(self, state, ap, vg, **kwargs):
        mat, = self.get_args(['material'], **kwargs)
        cache = self.get_cache('state_in_volume_qp', 0)
        state_qp = cache('state', self, 0,
                         state=state, get_vector=self.get_vector)

        return state_qp, mat, vg

class BiotStressQTerm(Term):
    r"""
    :Description:
    Biot stress tensor in quadrature points, given in the usual vector form
    exploiting symmetry: in 3D it has 6 components with the indices ordered as
    :math:`[11, 22, 33, 12, 13, 23]`, in 2D it has 3 components with the
    indices ordered as :math:`[11, 22, 12]`.
    
    :Definition:
    .. math::
        \alpha_{ij} \bar{p}|_{qp}

    :Arguments:
        material  : :math:`\alpha_{ij}`,
        parameter : :math:`\bar{p}`
    """
    name = 'dq_biot_stress'
    arg_types = ('material', 'parameter')
    use_caches = {'state_in_volume_qp' : [['parameter']]}

    def __call__(self, diff_var=None, chunk_size=None, **kwargs):
        if diff_var is not None:
            raise StopIteration

        mat, par = self.get_args(**kwargs)
        ap, vg = self.get_approximation(par)
        n_el, n_qp, dim, n_ep = ap.get_v_data_shape(self.integral)

        shape = (chunk_size, n_qp, dim * (dim + 1) / 2, 1)

        cache = self.get_cache('state_in_volume_qp', 0)
        state_qp = cache('state', self, 0,
                         state=par, get_vector=self.get_vector)

        for out, chunk in self.char_fun(chunk_size, shape):
            stress = mat[chunk] * state_qp[chunk]

            yield stress, chunk, 0


class BiotGradTH( CouplingVectorScalarTH ):

    def get_fargs_grad( self, diff_var = None, chunk_size = None, **kwargs ):
        ts, mats, virtual, state = self.get_args( **kwargs )
        apr, vgr = self.get_approximation(virtual)
        apc, vgc = self.get_approximation(state)

        self.set_data_shape( apr, apc )
        shape, mode = self.get_shape_grad( diff_var, chunk_size )

        if (ts.step == 0) and (mode == 0):
            raise StopIteration

        bf = apc.get_base('v', 0, self.integral)
        n_el, n_qp = self.data_shape_r[:2]

        if mode == 1:
            aux = nm.array( [0], ndmin = 4, dtype = nm.float64 )
            mat = mats[0]
            mat = nm.tile(mat, (n_el, n_qp, 1, 1))
            return (ts.dt, aux, bf, mat, vgr), shape, mode

        else:
            cache = self.get_cache( 'state_in_volume_qp', 0 )
            def iter_kernel():
                for ii, mat in enumerate( mats ):
                    vec_qp = cache('state', self, ii,
                                   state=state, get_vector=self.get_vector)
                    mat = nm.tile(mat, (n_el, n_qp, 1, 1))
                    yield ii, (ts.dt, vec_qp, bf, mat, vgr)
            return iter_kernel, shape, mode

class BiotDivTH( CouplingVectorScalarTH ):

    def get_fargs_div( self, diff_var = None, chunk_size = None, **kwargs ):
        ts, mats, state, virtual = self.get_args( **kwargs )
        apr, vgr = self.get_approximation(virtual)
        apc, vgc = self.get_approximation(state)

        self.set_data_shape( apr, apc )
        shape, mode = self.get_shape_div( diff_var, chunk_size )

        if (ts.step == 0) and (mode == 0):
            raise StopIteration

        bf = apr.get_base('v', 0, self.integral)
        n_el, n_qp = self.data_shape_r[:2]

        if mode == 1:
            aux = nm.array( [0], ndmin = 4, dtype = nm.float64 )
            mat = mats[0]
            mat = nm.tile(mat, (n_el, n_qp, 1, 1))
            return (ts.dt, aux, bf, mat, vgc), shape, mode

        else:
            cache = self.get_cache( 'cauchy_strain', 0 )
            def iter_kernel():
                for ii, mat in enumerate( mats ):
                    strain = cache('strain', self, ii,
                                   state=state, get_vector=self.get_vector)
                    mat = nm.tile(mat, (n_el, n_qp, 1, 1))
                    yield ii, (ts.dt, strain, bf, mat, vgc)
            return iter_kernel, shape, mode

class BiotTHTerm( BiotGradTH, BiotDivTH, Term ):
    r"""
    :Description:
    Fading memory Biot term. Can use derivatives.

    :Definition:
    .. math::
        \begin{array}{l}
        \int_{\Omega} \left [\int_0^t \alpha_{ij}(t-\tau)\,p(\tau)) \difd{\tau}
        \right]\,e_{ij}(\ul{v}) \mbox{ ,} \\
        \int_{\Omega} \left [\int_0^t
        \alpha_{ij}(t-\tau) e_{kl}(\ul{u}(\tau)) \difd{\tau} \right] q
        \end{array}

    :Arguments 1:
        ts       : :class:`TimeStepper` instance,
        material : :math:`\alpha_{ij}(\tau)`,
        virtual  : :math:`\ul{v}`,
        state    : :math:`p`

    :Arguments 2:
        ts       : :class:`TimeStepper` instance,
        material : :math:`\alpha_{ij}(\tau)`,
        state    : :math:`\ul{u}`,
        virtual  : :math:`q`
    """
    name = 'dw_biot_th'
    arg_types = (('ts', 'material', 'virtual', 'state'),
                 ('ts', 'material', 'state', 'virtual'))
    modes = ('grad', 'div')

    def set_arg_types( self ):
        """Dynamically inherits from either BiotGradTH or
        BiotDivTH."""
        if self.mode == 'grad':
            self.function = terms.dw_biot_grad
            use_method_with_name( self, self.get_fargs_grad, 'get_fargs' )
            self.use_caches = {'state_in_volume_qp' : [['state',
                                                        {'state' : (-1,-1)}]]}
        elif self.mode == 'div':
            self.function = terms.dw_biot_div
            use_method_with_name( self, self.get_fargs_div, 'get_fargs' )
            self.use_caches = {'cauchy_strain' : [['state',
                                                   {'strain' : (-1,-1)}]]}
        else:
            raise NotImplementedError

class BiotGradETH( CouplingVectorScalar ):

    def get_fargs_grad( self, diff_var = None, chunk_size = None, **kwargs ):
        ts, mat0, mat1, virtual, state = self.get_args( **kwargs )
        apr, vgr = self.get_approximation(virtual)
        apc, vgc = self.get_approximation(state)

        self.set_data_shape( apr, apc )
        shape, mode = self.get_shape_grad( diff_var, chunk_size )

        bf = apc.get_base('v', 0, self.integral)
        if diff_var is None:
            cache = self.get_cache( 'state_in_volume_qp', 0 )
            vec_qp = cache('state', self, 0,
                           state=state, get_vector=self.get_vector)

            cache = self.get_cache('exp_history', 0)
            increment = cache('increment', self, 0,
                              decay=mat1, values=vec_qp)
            history = cache('history', self, 0)

            fargs = (ts.dt, history + increment, bf, mat0, vgr)
            if ts.step == 0: # Just init the history in step 0.
                raise StopIteration

        else:
            aux = nm.array( [0], ndmin = 4, dtype = nm.float64 )
            fargs = (ts.dt, aux, bf, mat0, vgr)

        return fargs, shape, mode

class BiotDivETH( CouplingVectorScalar ):

    def get_fargs_div( self, diff_var = None, chunk_size = None, **kwargs ):
        ts, mat0, mat1, state, virtual = self.get_args( **kwargs )
        apr, vgr = self.get_approximation(virtual)
        apc, vgc = self.get_approximation(state)

        self.set_data_shape( apr, apc )
        shape, mode = self.get_shape_div( diff_var, chunk_size )

        bf = apr.get_base('v', 0, self.integral)
        if diff_var is None:
            cache = self.get_cache( 'cauchy_strain', 0 )
            strain = cache('strain', self, 0,
                           state=state, get_vector=self.get_vector)

            cache = self.get_cache('exp_history', 0)
            increment = cache('increment', self, 0,
                              decay=mat1, values=strain)
            history = cache('history', self, 0)

            fargs = (ts.dt, history + increment, bf, mat0, vgc)
            if ts.step == 0: # Just init the history in step 0.
                raise StopIteration

        else:
            aux = nm.array( [0], ndmin = 4, dtype = nm.float64 )
            fargs = (ts.dt, aux, bf, mat0, vgc)

        return fargs, shape, mode

class BiotETHTerm( BiotGradETH, BiotDivETH, Term ):
    r"""
    :Description:
    This term has the same definition as dw_biot_th, but assumes an
    exponential approximation of the convolution kernel resulting in much
    higher efficiency. Can use derivatives.

    :Definition:
    .. math::
        \begin{array}{l}
        \int_{\Omega} \left [\int_0^t \alpha_{ij}(t-\tau)\,p(\tau)) \difd{\tau}
        \right]\,e_{ij}(\ul{v}) \mbox{ ,} \\
        \int_{\Omega} \left [\int_0^t
        \alpha_{ij}(t-\tau) e_{kl}(\ul{u}(\tau)) \difd{\tau} \right] q
        \end{array}
    
    :Arguments 1:
        ts         : :class:`TimeStepper` instance,
        material_0 : :math:`\alpha_{ij}(0)`,
        material_1 : :math:`\exp(-\lambda \Delta t)` (decay at :math:`t_1`),
        virtual    : :math:`\ul{v}`,
        state      : :math:`p`

    :Arguments 2:
        ts         : :class:`TimeStepper` instance,
        material_0 : :math:`\alpha_{ij}(0)`,
        material_1 : :math:`\exp(-\lambda \Delta t)` (decay at :math:`t_1`),
        state      : :math:`\ul{u}`,
        virtual    : :math:`q`
    """
    name = 'dw_biot_eth'
    arg_types = (('ts', 'material_0', 'material_1', 'virtual', 'state'),
                 ('ts', 'material_0', 'material_1', 'state', 'virtual'))
    modes = ('grad', 'div')
    use_caches = {'exp_history' : [['material_0', 'material_1', 'state']]}

    def set_arg_types( self ):
        """Dynamically inherits from either BiotGradETH or
        BiotDivETH."""
        if self.mode == 'grad':
            self.function = terms.dw_biot_grad
            use_method_with_name( self, self.get_fargs_grad, 'get_fargs' )
            use_caches = {'state_in_volume_qp' : [['state']]}
        elif self.mode == 'div':
            self.function = terms.dw_biot_div
            use_method_with_name( self, self.get_fargs_div, 'get_fargs' )
            use_caches = {'cauchy_strain' : [['state']]}
        else:
            raise NotImplementedError

        self.use_caches.update(use_caches)
