# -*- coding: utf-8 -*-

"""Lover's Base API and database model.

TODO:Fix this docstring.
"""

import enum
from typing import Tuple, Optional

import sqlalchemy as sql
import sqlalchemy.engine as sql_engine
import sqlalchemy.ext.declarative as sql_decl
import sqlalchemy.ext.orderinglist as sql_ordlist
import sqlalchemy.orm as sql_orm

### SQLAlchemy setup

# Enable pragmas on SQLite
@sql.event.listens_for(sql_engine.Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enables foreign key support on SQLite.

    Args:
        Undocumented

    Returns:
        None
    """

    del connection_record # Unused

    if dbapi_connection.engine.driver != 'pysqlite':
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

### Session management ###

_Session = sql_orm.sessionmaker()

class LoversBase:
    """Lovers' database manager class.

    This class is the entry point to lovers_base. Creating a LoversBase object
    initializes a connection to the database.
    """

    def __init__(self, database: str, verbose: bool = False):
        """Crate a LoversBase object and initiate the connection to database.

        Args:
            database: The database to connect to (use SQLAlchemy syntax)
        """
        self._engine = sql.create_engine(database, echo=verbose)
        _Session.configure(bind=self._engine)
        self._session = _Session()

        # Create missing tables
        _Base.metadata.create_all(self._engine)

### Database model

class Genitalia(enum.Enum):
    """Type of a person's genitalia.

    This is very rough approximation which does not scale very well to
    intersex individuals.
    """

    female = 'female'
    male = 'male'
    other = 'other'

_Base = sql_decl.declarative_base()

class Individual(_Base):

    """An identifier number without any personal data.

    The table of individuals is usded to allocate unique id numbers for persons
    and participants, at the same time making sure, that all tables which use
    this id share it with each other, and can use it as their primary keys.

    When creating a new person/participant, a new id needs to be allocated
    from this table first. This can very easily be done with code like:

    >>> Person (individual=Individual())

    Column attributes:
    id: The unique individual ID

    Relationship attributes:
    person: Identifying information about a person
    participant:Participation information about the person

    """

    __tablename__ = "person_id"

    id = sql.Column(sql.Integer, primary_key=True)

    person = sql_orm.relation(lambda: Person, uselist=False, back_populates="individual")
    participant = sql_orm.relation(lambda: Participant, uselist=False, back_populates="individual")

    def __repr__(self) -> str:
        if self.person:
            person = f"Person={repr(self.person.name)}"
        else:
            person = None

        if self.participant:
            participant = "with participant record"
        else:
            participant = "without participant record"

        return f"<class {type(self).__name__}(id={self.id}, {person} {participant}>"

class Person(_Base):

    """Personal information that is needed to communicate with a person.

    This record will be purged if a person asks their data to be anonymized.

    Column attributes:
    id: Unique identifier (primary and foreign key, referring to individual.id)
    first_names: Person's first names
    last_name: Person's last name
    nickname: The name with which this person wants to be called
    email: E-mail address to which the person wants to receive our communications
    phone: The number the person wants us to use for contacting them
    allergies: Allergies of this person

    Relationship attributes:
    individual: The source of this person's id
    languages: The list of languages spoken by this user
    participant: Information about this person that is linked to participating sexual events
    notes: A list of various notes related to this user (information for event
        organizers/personal data administrators) [TODO: not implemented yet]

    Other attributes:
    name: A convenience attribute containign nickname and last name separated by a space
    """

    __tablename__ = 'person'

    id = sql.Column(sql.Integer, sql.ForeignKey('individual.id'), primary_key=True)
    first_names = sql.Column(sql.Unicode(120), nullable=False)
    last_name = sql.Column(sql.Unicode(120), nullable=False)
    nickname = sql.Column(sql.Unicode(120), nullable=False)
    email = sql.Column(sql.Unicode(120), nullable=False)
    phone = sql.Column(sql.Unicode(120), nullable=True)
    allergies = sql.Column(sql.Unicode(1024))

    languages = sql_orm.relationship(
        lambda: LanguageProficiency,
        foreign_keys='person_id',
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: LanguageProficiency.priority,
        collection_class=sql_ordlist.ordering_list('priority'))
    participant = sql_orm.relationship(
        lambda: Participant,
        uselist=False,
        back_populates='person')

    @property
    def name(self) -> str:
        """Returns:
            nickname + name
        """
        return f"{self.nickname} {self.last_name}"

    def __repr__(self) -> str:
        return f"<class {type(self).__name__}(id={self.id}, name={repr(self.name)})>"

class LanguageProficiency(_Base):
    """Description of a person's language skills.

    Column attributes:
    id: Languaeg definition id (primary key)
    person_id: The person this information applies to
    priority: Priority of this language relative to the person
    language: Two-letter ISO language code

    Reference attributes:
    person: The person to which this language proficiency definition applies to
    """

    __tablename__ = 'language_proficiency'

    id = sql.Column(sql.Integer, primary_key=True)
    person_id = sql.Column(sql.Integer,
                           sql.ForeignKey('person.id', ondelete='CASCADE'))
    priority = sql.Column(sql.Integer)
    language = sql.Column(sql.Unicode(2), nullable=False)

    def __repr__(self) -> str:
        return (f"<class {type(self).__name__}"
                f"(person_id={self.person_id}, lang={self.language},"
                f" priority={self.priority})>"
                )

class Participant(_Base):
    """Participant is a (possibly anonymous) person who has been registered for
    wanting to attend an event.

    If the person column is defined, the Participant has an identity. If the
    person column is None, the real person behind this participant has
    requested that their information be anonymized.

    Column attributes:
    id: Individual ID
    birth_year: Year of birth
    genitalia: Type of genitalia

    Reference attributes:
    orientation: Sexual orientation
    person: Identity and contact information for this participant
    participations: List of participations
    """

    __tablename__ = 'participant'

    id = sql.Column(sql.Integer, sql.ForeignKey('individual.id'), primary_key=True)
    birth_year = sql.Column(sql.Integer)
    genitalia = sql.Column(sql.Enum(Genitalia), nullable=False)

    orientation = sql_orm.relation(
        lambda: Orientation,
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False)
    person = sql_orm.relationship(
        lambda: Person,
        uselist=False,
        back_populates='participant')
    participations = sql_orm.relationship(
        lambda: Participation,
        foreign_keys='participant_id',
        order_by='participation.id',
        back_populates='participant')

class Orientation(_Base):
    """Description of a participant's sexual orientation.

    This is a very rough model which only describes the participant's
    orientation towards specific genitalia types. It has no relationship with
    the gender(s) of the target person. The comment field may be used to
    denote additional information.

    Column attributes:
    id: Participant's id (primary and foreign key)
    female: Atractiveness of female genitalia
    male: Atractiveness of male genitalia
    other: Atractiveness of other kinds of genitalia
    """

    __tablename__ = 'orientation'

    id = sql.Column(sql.Integer,
                    sql.ForeignKey('participant.id', ondelete="CASCADE"),
                    primary_key=True)
    female = sql.Column(sql.Integer)
    male = sql.Column(sql.Integer)
    other = sql.Column(sql.Integer)
    comment = sql.Column(sql.Unicode(1024))

    def __repr__(self) -> str:
        return (f"<class {type(self).__name__}(id={self.id},"
                f" female={self.female}, male={self.male}, other={self.other}>"
                )
class EventType(enum.Enum):
    """Types of events organized."""

    art_project = 'art_project'
    gentle_orgy = 'gentle_orgy'
    meeting = 'meeting'
    workshop = 'workshop'

class Event(_Base):
    """Event description.

    This class describes events that are to be organized. Stored information
    includes both practical event details (such as time and location) as well
    as participation registration info.

    Column attributes:
    id: Event identifier (integer primary key)
    name: Human-readable identifier string (unique)
    kind: Type of the event
    start_time: Starting time
    end_time: Ending time
    location_id: Identifier to the location information table
    language: Spoken language in common programme (two-letter ISO language code)

    Reference attributes:
    location: Location information
    participations: List of participation records
    """

    __tablename__ = 'event'

    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.Unicode(32), unique=True, nullable=False)
    kind = sql.Column(sql.Enum(EventType), nullable=False)
    start_time = sql.Column(sql.DateTime(timezone=True), nullable=False)
    end_time = sql.Column(sql.DateTime(timezone=True), nullable=False)
    location_id = sql.Column(sql.Integer, sql.ForeignKey('location.id'))
    language = sql.Column(sql.Unicode(2))

    location = sql_orm.relationship(
        lambda: Location,
        uselist=False,
        foreign_keys='Event.location_id')
    participations = sql_orm.relationship(
        lambda: Participation,
        order_by='parcipation.id',
        back_populates='event')

class Location(_Base):
    """Location information for an event venue.

    This class holds necessary information for book keeping. Descriptive
    details should be stored elsewhere.

    Column attributes:
    id: Location ID (referenced from events) (primary key)
    name: Human readable string representation of id (unique)
    address: Physical address of this venue
    """

    __tablename__ = "location"

    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.Unicode(32), unique=True, nullable=False)
    address = sql.Column(sql.Unicode(1024))

class Role(enum.Enum):
    """Role of a participant in an event.

    This is stored in the Participation record.
    """

    participant = 'participant'
    organizer = 'organizer'
    assistant = 'assistant'
    artist = 'artist'
    model = 'model'
    staff = 'staff'

class ParticipationStatus(enum.Enum):
    """Describes participation status of a participant.

    This is stored within the participation status log.
    """

    invited = 'invited'  # Invited by the organizers
    declined = 'declined'  # Declined from participating when invited
    signed = 'signed'  # Signed in to an event, awaiting for acceptance
    rejected = 'rejected'  # Signed in, but got rejected by the organizers
    queued = 'queued'  # Placed on waiting list
    accepted = 'accepted'  # Accepted to an event by organizers
    withdrew = 'withdrew'  # Withdrew when informed about acceptance
    cancelled = 'cancelled'  # Cancelled their participation (after sign up)
    faded = 'faded'  # Signed up, got accepted, but did not come to the event
    participated = 'participated'  # Participated the event

class Participation(_Base):
    """A participation is an association between a participant and an event.

    Every event has a list of participations – one entry per participant.
    Participation records the participant, the event and participation status
    log. This log is complemented with new entries as the user's status
    changes.

    Column attributes:
    id: Participation id (composite primary key)
    event_id: Event reference (unique foreign key)
    participant_id: Participant reference (unique foreign key)
    role: Participant's role in this event
    invitation_source_id: Participation ID of the person who invited this
        participant (self-referring foreign key). When this is None, the
        invitation originates from the organizers.
    notes: General notes about this participation – not related to its status

    Relationship attributes:
    event: The event reference
    participant: The participant reference
    status_log: List of status change attributes. The last one is the current
        status.
    blacklist: List of names of persons' whom with the participant does not
        want to attend this event
    invitation_source: Participation record referring to the inviter of this
        participant.
    invitation_targets: List of participation records for the persons this
        person has invited.

    Other attributes:
    status: Current participation status of the participant
    """

    __tablename__ = 'participation'

    id = sql.Column(sql.Integer, primary_key=True, autoincrement=True)
    event_id = sql.Column(sql.Integer, sql.ForeignKey('event.id'), unique=True, nullable=False)
    participant_id = sql.Column(sql.Integer, sql.ForeignKey('participant.id'),
                                unique=True,
                                nullable=False)
    role = sql.Column(sql.Enum(Role), nullable=False)
    invitation_source_id = sql.Column(sql.Integer, sql.ForeignKey('participation.id'))
    notes = sql.Column(sql.Unicode(1024))

    event = sql_orm.relationship(lambda: Event, uselist=False)
    participant = sql_orm.relationship(lambda: Event, uselist=False)
    status_log = sql_orm.relationship(
        lambda: StatusLog,
        foreign_keys='participation_id',
        #cascade="all, delete-orphan",  # Deletion should not happen
        #passive_deletes=True,  # Deletion should not happen
        order_by=lambda: StatusLog.order,
        collection_class=sql_ordlist.ordering_list('order'))
    invitation_targets = sql_orm.relationship(
        lambda: Participation,
        remote_side=[id],
        backref='invitation_source')

    def get_companions(self) -> Tuple[Participant]:
        """Returns companions from this Participation.

        Returns:
            A tuple of Participant objects.
        """
        return tuple((target.participant
                      for target in self.invitation_targets))

    def get_inviter(self) -> Optional[Participant]:
        """Returns the inviter for this Participation, or None if not
        present.
        """
        source = self.invitation_source
        return source.participant if source is not None else None

    @property
    def status(self) -> ParticipationStatus:
        """Returns the current status for this Participation."""
        return self.status_log[-1].status

class StatusLog(_Base):
    """Log of participation status changes of a participant within an event.

    This log stores details about status updates of a participant regarding
    their participation to an event. Status log entries form an ordered list
    to which new status changes are added to. Existing entries in the log
    should not be deleted. The latest entry (the entry with highest position
    number) represents the current participation status.

    Column attributes:
    participation_id: The participation to which this entry refers to
        (composite primary key).
    position: The position of this entry in the list for the particular
        participation (composite primary key).
    timestamp: The time when this status update was received (not the moment
        of recording it)
    status: The new status
    notes: Notes recorded by the organizers related to this change
    """

    __tablename__ = 'status_log'

    participation_id = sql.Column(sql.Integer,
                                  sql.ForeignKey('participation.id'),
                                  primary_key=True)
    position = sql.Column(sql.Integer,
                          primary_key=True,
                          autoincrement=True)
    timestamp = sql.Column(sql.DateTime(timezone=True))
    status = sql.Column(sql.Enum(ParticipationStatus), nullable=False)
    notes = sql.Column(sql.Unicode(1024))
