from app import db
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.ext.declarative import declared_attr
import json
import os

class Serializeable(object):
    @property
    def serialized(self) :
        blacklist = ['_sa_instance_state']
        blacklist.extend(getattr(self, '_serialize_blacklist', []))
        result = {}
        for k in self.__public__:
            v = getattr(self, k)
            if k in blacklist:
                continue
            elif isinstance(v, list):
                result[k] = [i.serialized for i in v]
            elif isinstance(v, db.Model):
                result[k] = v.serialized
            else:
                result[k] = v

        return result
    def toJson(self):
        return json.dumps(self.serialized)
    def _asdict(self):
        return self.serialized

def dump_datetime(value):
    """Deserialize datetime object into string form for JSON processing."""
    if value is None:
        return None
    return value.strftime("%d/%m/%Y") + " " + value.strftime("%H:%M:%S")

class Task(Serializeable, db.Model):
    __tablename__ = 'engine_task'
    __public__ = ['id',
                    'name',
                    'size',
                    'path',
                    'mode',
                    'owner',
                    'assignee',
                    'bug_tracker' ,
                    'created_date',
                    'updated_date',
                    'overlap',
                    'z_order',
                    'flipped',
                    'source',
                    'status',
                    'project',
                    'score',
                    'last_viewed_frame',
                    'video_id']

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    size = db.Column(db.Integer)
    path = db.Column(db.String(256))
    mode = db.Column(db.String(32))
    owner_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))
    assignee_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))
    bug_tracker = db.Column(db.String(2000), default="")
    created_date = db.Column(db.DateTime(), server_default=db.func.now())
    updated_date = db.Column(db.DateTime(), server_default=db.func.now())
    overlap = db.Column(db.Integer, default=0)
    z_order = db.Column(db.Boolean(), default=False)
    flipped = db.Column(db.Boolean(), default=False)
    source = db.Column(db.String(256), default="unknown")
    status = db.Column(db.String(32), default="annotation")
    project_id = db.Column(db.Integer, db.ForeignKey('engine_projects.id'), default=1)
    score = db.Column(db.Float, default=0)
    last_viewed_frame = db.Column(db.Integer, default=0)
    video_id = db.Column(db.Integer, default=-1)

    def get_data_dirname(self):
        return os.path.join(self.path, "data")

class Tasksource(Serializeable, db.Model):
    __tablename__ = 'engine_tasksource'
    __public__ = ['id',
                    'task',
                    'source_name',
                    'frame']
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('engine_task.id'))

    task = db.relationship('Task', uselist=False, foreign_keys = 'Tasksource.task_id')
    source_name = db.Column(db.String(256))
    frame = db.Column(db.Integer)

class Projects(Serializeable, db.Model):
    __tablename__ = 'engine_projects'
    __public__ = ['id',
                    'name',
                    'has_score']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    has_score = db.Column(db.Boolean())
    project_tasks = db.relationship('Task', backref='project', lazy='dynamic')

class User(Serializeable, db.Model):
    __tablename__ = 'auth_user'
    __public__ = ['id' ,
                    'last_login',
                    'is_superuser',
                    'username',
                    'first_name',
                    'last_name',
                    'email' ,
                    'is_staff' ,
                    'is_active',
                    'date_joined']

    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(128))
    last_login = db.Column(db.DateTime())
    is_superuser = db.Column(db.Boolean())
    username = db.Column(db.String(150), unique=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(150))
    email = db.Column(db.String(254))
    is_staff =  db.Column(db.Boolean())
    is_active = db.Column(db.Boolean())
    date_joined = db.Column(db.DateTime())
    owner_tasks = db.relationship('Task', backref='owner', lazy='dynamic', foreign_keys = 'Task.owner_id')
    assignee_tasks = db.relationship('Task', backref='assignee', lazy='dynamic', foreign_keys = 'Task.assignee_id')

class Group(Serializeable, db.Model):
    __tablename__ = 'auth_group'
    __public__ = ['id',
                    'name']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))

class User_groups(Serializeable, db.Model):
    __tablename__ = 'auth_user_groups'
    __public__ = ['id',
                    'user',
                    'user_id',
                    'group',
                    'group_id']
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('auth_group.id'))

    user = db.relationship('User', uselist=False, foreign_keys = 'User_groups.user_id')
    group = db.relationship('Group', uselist=False, foreign_keys = 'User_groups.group_id')

class Frameproperties(Serializeable, db.Model):
    __tablename__ = 'engine_frameproperties'
    __public__ = [ 'id', 'prop', 'value', 'parent_id', 'project']
    id = db.Column(db.Integer, primary_key=True)
    prop = db.Column(db.String(256))
    value = db.Column(db.String(256))
    parent_id = db.Column(db.Integer)
    project_id = db.Column(db.Integer, db.ForeignKey('engine_projects.id'))

    project = db.relationship('Projects', uselist=False, foreign_keys = 'Frameproperties.project_id')


# class Framevals(Serializeable, db.Model):
#     __tablename__ = 'engine_framevals'
#     __public__ = [ 'id', 'name']
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(256))

# class Framepropvals(Serializeable, db.Model):
#     __tablename__ = 'engine_framepropvals'
#     __public__ = [ 'id', 'prop', 'val']
#     id = db.Column(db.Integer, primary_key=True)
#     prop_id = db.Column(db.Integer, db.ForeignKey('engine_frameprops.id'))
#     val_id = db.Column(db.Integer, db.ForeignKey('engine_framevals.id'))

#     prop = db.relationship('FrameProps', uselist=False, foreign_keys = 'Framepropvals.prop_id')
#     val = db.relationship('Framevals', uselist=False, foreign_keys = 'Framepropvals.val_id')

class Taskframespec(Serializeable, db.Model):
    __tablename__ = 'engine_taskframespec'
    __public__ = ['id',
                    'task',
                    'propVal']
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('engine_task.id'))
    propVal_id = db.Column(db.Integer, db.ForeignKey('engine_frameproperties.id'))

    task = db.relationship('Task', uselist=False, foreign_keys = 'Taskframespec.task_id')
    propVal = db.relationship('Frameproperties', uselist=False, foreign_keys = 'Taskframespec.propVal_id')

class Keyframespec(Serializeable, db.Model):
    __tablename__ = 'engine_keyframespec'
    __public__ = [ 'id',
                    'frame',
                    'frameSpec']
    id = db.Column(db.Integer, primary_key=True)
    frame = db.Column(db.Integer)
    frameSpec_id = db.Column(db.Integer, db.ForeignKey('engine_taskframespec.id'))

    frameSpec = db.relationship('Taskframespec', uselist=False, foreign_keys = 'Keyframespec.frameSpec_id')
       
class Objectstorages(Serializeable, db.Model):
    __tablename__ = 'engine_objectstorages'
    __public__ = [ 'id', 'name']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    secret_key = db.Column(db.String(256))
    access_key = db.Column(db.String(256))

class Projects_users(Serializeable, db.Model):
    __tablename__ = 'engine_projects_users'
    __public__ = ['id',
                    'project',
                    'user']
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('engine_projects.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))

    project = db.relationship('Projects', uselist=False, foreign_keys = 'Projects_users.project_id')
    user = db.relationship('User', uselist=False, foreign_keys = 'Projects_users.user_id')

class Projects_objectstorages(Serializeable, db.Model):
    __tablename__ = 'engine_projects_objectstorages'
    __public__ = ['id',
                    'project',
                    'object_storage',
                    'channels']
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('engine_projects.id'))
    object_storage_id = db.Column(db.Integer, db.ForeignKey('engine_objectstorages.id'))
    channels = db.Column(db.ARRAY(db.String(256)))

    project = db.relationship('Projects', uselist=False, foreign_keys = 'Projects_objectstorages.project_id')
    object_storage = db.relationship('Objectstorages', uselist=False, foreign_keys = 'Projects_objectstorages.object_storage_id')

class Labeltypes(Serializeable, db.Model):
    __tablename__ = 'engine_labeltypes'
    __public__ = [ 'id', 'label', 'attribute', 'value', 'project']
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(256))
    attribute = db.Column(db.String(256))
    value = db.Column(db.String(256))
    project_id = db.Column(db.Integer, db.ForeignKey('engine_projects.id'))

    project = db.relationship('Projects', uselist=False, foreign_keys = 'Labeltypes.project_id')


class Attributedetails(Serializeable, db.Model):
    __tablename__ = 'engine_attributedetails'
    __public__ = ['id',
                    'can_change',
                    'labelType']
    id = db.Column(db.Integer, primary_key=True)
    can_change = db.Column(db.Boolean()) 
    labelType_id = db.Column(db.Integer, db.ForeignKey('engine_labeltypes.id'))

    labelType = db.relationship('Labeltypes', uselist=False, foreign_keys = 'Attributedetails.labelType_id')


class Labeldetails(Serializeable, db.Model):
    __tablename__ = 'engine_labeldetails'
    __public__ = ['id',
                    'color',
                    'catagory'
                    'labelType']
    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(256))
    catagory = db.Column(db.String(256))
    labelType_id = db.Column(db.Integer, db.ForeignKey('engine_labeltypes.id'))

    labelType = db.relationship('Labeltypes', uselist=False, foreign_keys = 'Labeldetails.labelType_id')

# class Vals(Serializeable, db.Model):
#     __tablename__ = 'engine_vals'
#     __public__ = ['id', 'name']
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(256))

# class Labelattrs(Serializeable, db.Model):
#     __tablename__ = 'engine_labelattrs'
#     __public__ = ['id',
#                     'label',
#                     'attribute']
#     id = db.Column(db.Integer, primary_key=True)
#     label_id = db.Column(db.Integer, db.ForeignKey('engine_labels.id'))
#     attribute_id = db.Column(db.Integer, db.ForeignKey('engine_attrs.id'))

#     label = db.relationship('Labels', uselist=False, foreign_keys = 'Labelattrs.label_id')
#     attribute = db.relationship('Attrs', uselist=False, foreign_keys = 'Labelattrs.attribute_id')

# class Labelattrvalues(Serializeable, db.Model):
#     __tablename__ = 'engine_labelattrvalues'
#     __public__ = ['id' ,
#                     'labelAttribute',
#                     'value']
#     id = db.Column(db.Integer, primary_key=True)
#     labelAttribute_id = db.Column(db.Integer, db.ForeignKey('engine_labelattrs.id'))
#     value_id = db.Column(db.Integer, db.ForeignKey('engine_vals.id'))

#     labelAttribute = db.relationship('Labelattrs', uselist=False, foreign_keys = 'Labelattrvalues.labelAttribute_id')
#     value = db.relationship('Vals', uselist=False, foreign_keys = 'Labelattrvalues.value_id')

class Segment(Serializeable, db.Model):
    __tablename__ = 'engine_segment'
    __public__ = ['id',
                    'task',
                    'start_frame',
                    'stop_frame']
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('engine_task.id'))
    start_frame = db.Column(db.Integer)
    stop_frame = db.Column(db.Integer)


    task = db.relationship('Task', uselist=False, foreign_keys = 'Segment.task_id')

class Job(Serializeable, db.Model):
    __tablename__ = 'engine_job'
    __public__ = ['id',
                    'segment',
                    'status',
                    'max_shape_id']
    id = db.Column(db.Integer, primary_key=True)
    segment_id = db.Column(db.Integer, db.ForeignKey('engine_segment.id'))
    assignee_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))
    status = db.Column(db.String(32))
    max_shape_id = db.Column(db.BigInteger)

    segment = db.relationship('Segment', uselist=False, foreign_keys = 'Job.segment_id')
    assignee = db.relationship('User', uselist=False, foreign_keys = 'Job.assignee_id')

class Label(Serializeable, db.Model):
    __tablename__ = 'engine_label'
    __public__ = ['id',
                    'task',
                    'name']
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('engine_task.id'))
    name = db.Column(db.String(64))

    task = db.relationship('Task', uselist=False, foreign_keys = 'Label.task_id') 

class Attributespec(Serializeable, db.Model):
    __tablename__ = 'engine_attributespec'
    __public__ = ['id',
                    'label',
                    'text']
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('engine_label.id'))
    text = db.Column(db.String(1024))

    label = db.relationship('Label', uselist=False, foreign_keys = 'Attributespec.label_id')

class Attributeval(db.Model):
    __abstract__ = True

    @declared_attr
    def spec_id(self):
        return db.Column(db.Integer, db.ForeignKey('engine_attributespec.id'))

    @declared_attr
    def spec(self):
        return db.relationship('Attributespec')

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64))

    __mapper_args__ = {
        'polymorphic_identity' : 'attributeval'
    }


class Annotation(db.Model):
    __abstract__ = True

    @declared_attr
    def job_id(self):
        return db.Column(db.Integer, db.ForeignKey('engine_job.id'))
        
    @declared_attr
    def label_id(self):
        return db.Column(db.Integer, db.ForeignKey('engine_label.id'))

    @declared_attr
    def job(self):
        return db.relationship('Job')
        
    @declared_attr
    def label(self):
        return db.relationship('Label')

    id = db.Column(db.Integer, primary_key=True)
    frame = db.Column(db.Integer)
    group_id = db.Column(db.Integer)
    client_id = db.Column(db.BigInteger)

    __mapper_args__ = {
        'polymorphic_identity' : 'annotation'
    }

class Shape(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    occluded = db.Column(db.Boolean())
    z_order = db.Column(db.Integer)

class Boundingbox(Shape):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    xtl = db.Column(db.Float)
    ytl = db.Column(db.Float)
    xbr = db.Column(db.Float)
    ybr = db.Column(db.Float)

    __mapper_args__ = {
        'polymorphic_identity' : 'boundingbox'
    }

class Polyshape(Shape):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    points = db.Column(db.Text)

class Labeledbox(Serializeable, Annotation, Boundingbox):
    __tablename__ = 'engine_labeledbox'
    __public__ = ['id','occluded', 'z_order', 'frame', 'group_id', 'client_id', 'label', 'job', 'xtl','ytl', 'xbr', 'ybr']
    id = db.Column(db.Integer, db.ForeignKey('Annotation.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledbox'
    }

class Labeledboxattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_labeledboxattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'box']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    box_id = db.Column(db.Integer, db.ForeignKey('engine_labeledbox.id'))

    box = db.relationship('Labeledbox', uselist=False, foreign_keys = 'Labeledboxattributeval.box_id')
    
    __mapper_args__ = {
        'polymorphic_identity' : 'labeledboxattributeval'
    }

class Labeledpolygon(Serializeable, Annotation, Polyshape):
    __tablename__ = 'engine_labeledpolygon'
    __public__ = ['id', 'occluded', 'z_order', 'frame', 'group_id', 'client_id', 'label', 'job', 'points']
    id = db.Column(db.Integer, db.ForeignKey('Annotation.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpolygon'
    }

class Labeledpolygonattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_labeledpolygonattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'polygon']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    polygon_id = db.Column(db.Integer,  db.ForeignKey('engine_labeledpolygon.id'))

    polygon = db.relationship('Labeledpolygon', uselist=False, foreign_keys = 'Labeledpolygonattributeval.polygon_id')
    
    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpolygonattributeval'
    }

class Labeledpolyline(Serializeable, Annotation, Polyshape):
    __tablename__ = 'engine_labeledpolyline'
    __public__ = ['id', 'occluded', 'z_order', 'frame', 'group_id', 'client_id', 'label', 'job', 'points']
    id = db.Column(db.Integer, db.ForeignKey('Annotation.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpolyline'
    }


class Labeledpolylineattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_labeledpolylineattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'polyline']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    polyline_id = db.Column(db.Integer, db.ForeignKey('engine_labeledpolyline.id'))

    polyline = db.relationship('Labeledpolyline', uselist=False, foreign_keys = 'Labeledpolylineattributeval.polyline_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpolylineattributeval'
    }

class Labeledpoints(Serializeable, Annotation, Polyshape):
    __tablename__ = 'engine_labeledpoints'
    __public__ = ['id', 'occluded', 'z_order', 'frame', 'group_id', 'client_id', 'label', 'job', 'points']
    id = db.Column(db.Integer, db.ForeignKey('Annotation.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpoints'
    }

class Labeledpointsattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_labeledpointsattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'points']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    points_id = db.Column(db.Integer, db.ForeignKey('engine_labeledpoints.id'))

    points = db.relationship('Labeledpoints', uselist=False, foreign_keys = 'Labeledpointsattributeval.points_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'labeledpointsattributeval'
    }

class Objectpath(Serializeable, Annotation):
    __tablename__ = 'engine_objectpath'
    __public__ = ['id', 'frame', 'group_id', 'client_id', 'label', 'job', 'shapes']
    id = db.Column(db.Integer, primary_key=True)
    shapes = db.Column(db.String(10))

    __mapper_args__ = {
        'polymorphic_identity' : 'objectpath'
    }

class Objectpathattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_objectpathattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'track']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey('engine_objectpath.id'))

    track = db.relationship('Objectpath', uselist=False, foreign_keys = 'Objectpathattributeval.track_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'objectpathattributeval'
    }

class Trackedobject(db.Model):
    __abstract__ = True

    @declared_attr
    def track_id(self):
        return db.Column(db.Integer, db.ForeignKey('engine_objectpath.id'))

    @declared_attr
    def track(self):
        return db.relationship('Objectpath')

    id = db.Column(db.Integer, primary_key=True)
    frame = db.Column(db.Integer)
    outside = db.Column(db.Boolean())

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedobject'
    }

class Trackedbox(Serializeable, Trackedobject, Boundingbox):
    __tablename__ = 'engine_trackedbox'
    __public__ = ['id',
                    'occluded',
                    'z_order',
                    'track',
                    'frame',
                    'outside', 
                    'xtl',
                    'ytl', 
                    'xbr', 
                    'ybr']
    id = db.Column(db.Integer, db.ForeignKey('Trackedobject.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedbox'
    }

class Trackedboxattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_trackedboxattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'box']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    box_id = db.Column(db.Integer, db.ForeignKey('engine_trackedbox.id'))

    box = db.relationship('Trackedbox', uselist=False, foreign_keys = 'Trackedboxattributeval.box_id')
    
    __mapper_args__ = {
        'polymorphic_identity' : 'trackedboxattributeval'
    }

class Trackedpolygon(Serializeable, Trackedobject, Polyshape):
    __tablename__ = 'engine_trackedpolygon'
    __public__ = ['id',
                    'occluded',
                    'z_order',
                    'track',
                    'frame',
                    'outside',
                    'points']
    id = db.Column(db.Integer, db.ForeignKey('Trackedobject.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpolygon'
    }

class Trackedpolygonattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_trackedpolygonattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'polygon']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    polygon_id = db.Column(db.Integer, db.ForeignKey('engine_trackedpolygon.id'))

    polygon = db.relationship('Trackedpolygon', uselist=False, foreign_keys = 'Trackedpolygonattributeval.polygon_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpolygonattributeval'
    }

class Trackedpolyline(Serializeable, Trackedobject, Polyshape):
    __tablename__ = 'engine_trackedpolyline'
    __public__ = ['id',
                    'occluded',
                    'z_order',
                    'track',
                    'frame',
                    'outside',
                    'points']
    id = db.Column(db.Integer, db.ForeignKey('Trackedobject.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpolyline'
    }

class Trackedpolylineattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_trackedpolylineattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'polyline']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    polyline_id = db.Column(db.Integer, db.ForeignKey('engine_trackedpolyline.id'))

    polyline = db.relationship('Trackedpolyline', uselist=False, foreign_keys = 'Trackedpolylineattributeval.polyline_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpolylineattributeval'
    }

class Trackedpoints(Serializeable, Trackedobject, Polyshape):
    __tablename__ = 'engine_trackedpoints'
    __public__ = ['id',
                    'occluded',
                    'z_order',
                    'track',
                    'frame',
                    'outside',
                    'points']
    id = db.Column(db.Integer, db.ForeignKey('Trackedobject.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpoints'
    }

class Trackedpointsattributeval(Serializeable, Attributeval):
    __tablename__ = 'engine_trackedoointsattributeval'
    __public__ = ['id',
                    'spec' ,
                    'value',
                    'points']
    id = db.Column(db.Integer, db.ForeignKey('Attributeval.id'), primary_key=True)
    points_id = db.Column(db.Integer, db.ForeignKey('engine_trackedpoints.id'))

    points = db.relationship('Trackedpoints', uselist=False, foreign_keys = 'Trackedpointsattributeval.points_id')

    __mapper_args__ = {
        'polymorphic_identity' : 'trackedpointsattributeval'
    }