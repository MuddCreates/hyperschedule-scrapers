"""
Utility library for Hyperschedule scrapers. Contains the
maintainer-facing API for writing a scraper.
"""

import abc
import datetime
import functools
import numbers

import dateparser


from hyperschedule import util


class Log:
    """
    Class handling logging. Used both by the Hyperschedule library and
    by scrapers.
    """

    def _log(self, level, msg, *args, **kwargs):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        msg_str = msg.format(*args, **kwargs)
        print("{} [{}] {}".format(timestamp, level.upper(), msg_str))

    def info(self, msg, *args, **kwargs):
        self._log("info", msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self._log("warn", msg, *args, **kwargs)


# Global logging object.
log = Log()


class ImplementorError(Exception):
    """
    Exception raised when the maintainer misuses the Hyperschedule
    library.
    """

    def __init__(self, msg, *args, **kwargs):
        """
        Construct a new `ImplementorError`, passing the `msg`, `args`, and
        `kwargs` to `str.format`.
        """
        super().__init__(msg.format(*args, **kwargs))


@functools.total_ordering
class Date:
    """
    Class representing a specific day of the year. Immutable.
    """

    @staticmethod
    def _from_json(self, string):
        if string is None:
            return None
        return Date(string)

    def __init__(self, string):
        """
        Construct a date from the given `string`, trying very hard to make
        something sensible out of whatever you provide. Suggested
        format is YYYY-MM-DD, but anything might work.
        """
        try:
            dt = dateparser.parse(string)
            if dt is None:
                raise ValueError
        except ValueError:
            raise ImplementorError("Date got invalid string: {}", string) from None
        self._year = dt.year
        self._month = dt.month
        self._day = dt.day

    def _to_json(self):
        return "{}-{}-{}".format(self._year, self._month, self._day)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._year, self._month, self._day) == (
            other._year,
            other._month,
            other._day,
        )

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._year, self._month, self._day) < (
            other._year,
            other._month,
            other._day,
        )

    def __hash__(self):
        return hash((self._year, self._month, self._day))

    def __str__(self):
        return "{}-{}-{}".format(self._year, self._month, self._day)


@functools.total_ordering
class Time:
    """
    Class representing a specific time of day. Immutable.
    """

    @staticmethod
    def _from_json(self, string):
        if string is None:
            return None
        return Time(string)

    def __init__(self, string):
        """
        Construct a time from the given `string`, trying very hard to make
        something sensible out of whatever you provide. Suggested
        format is HH:MM, but anything might work.
        """
        try:
            dt = dateparser.parse(string)
            if dt is None:
                raise ValueError
        except ValueError:
            raise ImplementorError("Time got invalid string: {}", string) from None
        self._hour = dt.hour
        self._minute = dt.minute

    def _to_json(self):
        return "{:02d}:{:02d}".format(self._hour, self._minute)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._hour, self._minute) == (other._hour, other._minute)

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._hour, self._minute) < (other._hour, other._minute)

    def __hash__(self):
        return hash((self._hour, self._minute))

    def __str__(self):
        hour = (self._hour - 1) % 12 + 1
        minute = self._minute
        ampm = "AM" if self._hour < 12 else "PM"
        return "{}:{} {}".format(hour, minute, ampm)


@functools.total_ordering
class Weekdays:
    """
    Class representing some subset of the days of the week (Monday
    through Sunday).
    """

    CHARS = "MTWRFSU"

    @staticmethod
    def _from_json(string):
        if string is None:
            return None
        return Weekdays(string)

    def __init__(self, days=None):
        """
        Construct a new set of `Weekdays`. By default it is empty. If you
        pass `days`, it should be an iterable containing days to add
        to the `Weekdays`, for example "MWF".
        """
        self._days = set()
        if days is not None:
            for day in days:
                self.add_day(day)

    def add_day(self, day):
        """
        Add a day (a character from the string "MTWRFSU") to the set of
        `Weekdays`.
        """
        day = day.upper()
        if day not in Weekdays.CHARS:
            raise ImplementorError("add_day got invalid day: {}", day)
        if day in self._days:
            log.warn("add_day got same day more than once: {}", day)
        self._days.add(day)

    def _check_valid(self):
        """
        Raise `ImplementorError` unless this `Weekdays` object is suitable
        for embedding in other objects.
        """
        if not self._days:
            raise ImplementorError("Weekdays has no days")

    def _to_json(self):
        return "".join(sorted(self._days, key=lambda d: Weekdays.CHARS.index(d)))

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self._days == other._days

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return sorted(Weekdays.CHARS.index(d) for d in self._days) < sorted(
            Weekdays.CHARS.index(d) for d in other._days
        )

    def __hash__(self):
        return hash(tuple(sorted(self._days)))

    def __str__(self):
        return "".join(sorted(self._days, key=lambda d: Weekdays.CHARS.index(d)))


@functools.total_ordering
class Subterm:
    """
    Class representing either the entirety of a term or only a
    sub-part, in the abstract. Immutable. This class represents
    "full-term", "first half-term", "second half-term", and so on,
    without making reference to any specific term. For those simple
    cases, consider using the constants `FullTerm`, `FirstHalfTerm`,
    `SecondHalfTerm`, and so on.
    """

    @staticmethod
    def _from_json(lst):
        if lst is None:
            return None
        return Subterm(*lst)

    def __init__(self, *subterms):
        """
        Construct a new `Subterm` from the given arguments, booleans. The
        number of arguments is the number of parts into which the term
        is divided. If an argument is truthy, then that sub-term is
        included in this `Subterm`; if an argument is falsy, then it
        is not.

        For example:

        FullTerm = Subterm(True)
        FirstHalfTerm = Subterm(True, False)
        SecondHalfTerm = Subterm(False, True)
        """
        if not subterms:
            raise ImplementorError("Subterm got no arguments")
        if not any(subterms):
            raise ImplementorError("Subterm got no truthy arguments: {}", subterms)
        self._subterms = tuple(map(bool, subterms))

    def _to_json(self):
        return list(self._subterms)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self._subterms == other._subterms

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (len(self._subterms), self._subterms) < (
            len(other._subterms),
            other._subterms,
        )

    def __hash__(self):
        return hash(tuple(self._subterms))

    def __str__(self):
        fractions = [
            "{}/{}".format(idx + 1, len(self._subterms))
            for idx, included in enumerate(self._subterms)
            if included
        ]
        return ", ".join(fractions)


# Indicates that a course runs for the entire term.
FullTerm = Subterm(True)

# Indicates that a course runs for only the first half of the term.
FirstHalfTerm = Subterm(True, False)

# Indicates that a course runs for only the second half of the term.
SecondHalfTerm = Subterm(False, True)

# Indicates that a course runs for only the first third of the term.
FirstThirdTerm = Subterm(True, False, False)

# Indicates that a course runs for only the middle third of the term.
MiddleThirdTerm = Subterm(False, True, False)

# Indicates that a course runs for only the last third of the term.
LastThirdTerm = Subterm(False, False, True)

# Indicates that a course runs for the first two-thirds of the term.
FirstAndMiddleThirdTerms = Subterm(True, True, False)

# Indicates that a course runs for the last two-thirds of the term.
MiddleAndLastThirdTerms = Subterm(False, True, True)


@functools.total_ordering
class Session:
    """
    Class representing a single recurring meeting time for a course.
    """

    @staticmethod
    def _from_json(obj):
        if obj is None:
            return None
        return Session(
            start_date=Date._from_json(obj["scheduleStartDate"]),
            end_date=Date._from_json(obj["scheduleEndDate"]),
            weekdays=Weekdays._from_json(obj["scheduleDays"]),
            start_time=Time._from_json(obj["scheduleStartTime"]),
            end_time=Time._from_json(obj["scheduleEndTime"]),
            subterm=Subterm._from_json(obj["scheduleSubterms"]),
            location=obj["scheduleLocation"],
        )

    def __init__(
        self,
        start_date=None,
        end_date=None,
        weekdays=None,
        start_time=None,
        end_time=None,
        subterm=None,
        location=None,
    ):
        """
        Construct a new `Session`. By default most of the attributes are
        unset, including the required ones.

        The `start_date`, if given, is the `Date` on which the course
        session has its first meeting. If the `start_date` is not
        included in the `Weekdays` of the course, then the first
        meeting of the course session will fall on one of those
        `Weekdays`, but not before the `start_date`. This field is
        optional; if it is omitted, then the exported calendar event
        for the course sessionwill use the day of the export as the
        start date.

        The `end_date`, if given, is the `Date` on which the course
        session has its last meeting. If the `end_date` is not
        included in the `Weekdays` of the course, then the last
        meeting of the course session will fall on one of those
        `Weekdays`, but not after the `end_date`. This field is
        optional; if it is omitted, then the exported calendar event
        for the course session will repeat forever.

        The `weekdays`, if given, are the `Weekdays` on which the
        course session has meetings. This field is mandatory; set it
        with `set_weekdays` if you do not pass it here.

        The `start_time`, if given, is the `Time` at which the course
        session begins. This field is mandatory; set it with
        `set_start_time` if you do not pass it here.

        The `end_time`, if given, is the `Time` at which the course
        session ends. It must come after the `start_time`. This field
        is mandatory; set it with `set_end_time` if you do not pass it
        here.

        The `subterm`, if given, is a `Subterm` object representing
        the sub-part of the term during which the course session has
        meetings. This field is optional; if it is omitted, then it
        defaults to `FullTerm`.

        The `location`, if given, is a string noting the physical
        location of the meetings of the course session. This field is
        optional; if it is omitted then the course session will not
        have a location listed on the frontend.
        """
        self._start_date = None
        self._end_date = None
        self._weekdays = None
        self._start_time = None
        self._end_time = None
        self._subterm = FullTerm
        self._location = None
        if start_date is not None:
            self.set_start_date(start_date)
        if end_date is not None:
            self.set_end_date(end_date)
        if weekdays is not None:
            self.set_weekdays(weekdays)
        if start_time is not None:
            self.set_start_time(start_time)
        if end_time is not None:
            self.set_end_time(end_time)
        if subterm is not None:
            self.set_subterm(subterm)
        if location is not None:
            self.set_location(location)

    def set_dates(self, start_date, end_date):
        """
        Set the start and end `Date` objects for this course session.
        These dates bound the course meetings, subject to the session
        `Weekdays`. No course meetings occur before the `start_date`,
        and none occur after the `end_date`. The `end_date` must come
        after the `start_date`.
        """
        self.set_start_date(start_date)
        self.set_end_date(end_date)

    def set_times(self, start_time, end_time):
        """
        Set the start and end `Time` objects for this course session. The
        `end_time` must come after the `start_time`.
        """
        self.set_start_time(start_time)
        self.set_end_time(end_time)

    def set_start_date(self, start_date):
        """
        Set the start `Date` for this course session. No course meetings
        will occur before the `start_date`.
        """
        if not isinstance(start_date, Date):
            raise ImplementorError("set_start_date got non-Date: {}", start_date)
        self._start_date = start_date
        self._check_dates()

    def set_end_date(self, end_date):
        """
        Set the end `Date` for this course session. No course meetings
        will occur after the `end_date`.
        """
        if not isinstance(end_date, Date):
            raise ImplementorError("set_end_date got non-Date: {}", end_date)
        self._end_date = end_date
        self._check_dates()

    def set_weekdays(self, weekdays):
        """
        Set the `Weekdays` for this course session. The course will only
        meet on these days. You must call this method if you did not
        pass `weekdays` when constructing the `Session`.
        """
        if not isinstance(weekdays, Weekdays):
            raise ImplementorError("set_weekdays got non-Weekdays: {}", weekdays)
        weekdays._check_valid()
        self._weekdays = weekdays

    def set_start_time(self, start_time):
        """
        Set the start `Time` for this course session.
        """
        if not isinstance(start_time, Time):
            raise ImplementorError("set_start_time got non-Time: {}", start_time)
        self._start_time = start_time
        self._check_times()

    def set_end_time(self, end_time):
        """
        Set the end `Time` for this course session.
        """
        if not isinstance(end_time, Time):
            raise ImplementorError("set_end_time got non-Time: {}", end_time)
        self._end_time = end_time
        self._check_times()

    def set_subterm(self, subterm):
        """
        Set the `Subterm` for this course session. By default, courses are
        `FullTerm`.
        """
        if not isinstance(subterm, Subterm):
            raise ImplementorError("set_subterm got non-Subterm: {}", subterm)
        self._subterm = subterm

    def set_location(self, location):
        """
        Set the location for this course session, a string.
        """
        if not isinstance(location, str):
            raise ImplementorError("set_location got non-string: {}", location)
        self._location = location

    def _check_dates(self):
        """
        Raise `ImplementorError` if `start_date` and `end_date` are both
        set and `start_date` is not before `end_date`.
        """
        if self._start_date is not None and self._end_date is not None:
            if self._start_date >= self._end_date:
                raise ImplementorError(
                    "Session start date not before end date: {} >= {}",
                    self._start_date,
                    self._end_date,
                )

    def _check_times(self):
        """
        Raise `ImplementorError` if `start_time` and `end_time` are both
        set and `start_time` is not before `end_time`.
        """
        if self._start_time is not None and self._end_time is not None:
            if self._start_time >= self._end_time:
                raise ImplementorError(
                    "Session start time not before end time: {} >= {}",
                    self._start_time,
                    self._end_time,
                )

    def _check_valid(self):
        """
        Raise `ImplementorError` if `start_time`, `end_time`, and
        `weekdays` are not all set.
        """
        if self._start_time is None:
            raise ImplementorError("Session missing start time")
        if self._end_time is None:
            raise ImplementorError("Session missing end time")
        if self._weekdays is None:
            raise ImplementorError("Session missing Weekdays")

    def _to_json(self):
        return {
            "scheduleStartDate": self._start_date,
            "scheduleEndDate": self._end_date,
            "scheduleWeekdays": self._weekdays,
            "scheduleStartTime": self._start_time,
            "scheduleEndTime": self._end_time,
            "scheduleSubterm": self._subterm,
            "scheduleLocation": self._location,
        }

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self._weekdays,
            self._start_time,
            self._end_time,
            self._subterm,
            self._location,
            self._start_date,
            self._end_date,
        ) == (
            other._weekdays,
            other._start_time,
            other._end_time,
            other._subterm,
            other._location,
            other._start_date,
            other._end_date,
        )

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self._weekdays,
            self._start_time,
            self._end_time,
            self._subterm,
            self._location,
            self._start_date,
            self._end_date,
        ) < (
            other._weekdays,
            other._start_time,
            other._end_time,
            other._subterm,
            other._location,
            other._start_date,
            other._end_date,
        )

    def __hash__(self):
        return hash(
            (
                self._start_date,
                self._end_date,
                self._weekdays,
                self._start_time,
                self._end_time,
                self._subterm,
                self._location,
            )
        )

    def __str__(self):
        groups = []
        group = []
        if self._weekdays is not None:
            group.append(str(self._weekdays))
        if self._start_time is not None:
            group.append(str(self._start_time))
        if self._start_time is not None and self._end_time is not None:
            group.append("-")
        if self._end_time is not None:
            group.append(str(self._end_time))
        if group:
            groups.append(group)
            group = []
        if self._start_date is not None:
            group.append(str(self._start_date))
        if self._start_date is not None and self._end_date is not None:
            group.append("-")
        if self._end_date is not None:
            group.append(str(self._end_date))
        if group:
            groups.append(group)
            group = []
        if self._subterm != FullTerm:
            groups.append(str(self._subterm))
        if self._location is not None:
            groups.append(self._location)
        return ", ".join(" ".join(group) for group in groups) or "(blank Meeting)"


@functools.total_ordering
class Schedule:
    """
    Class representing the set of all of a course's scheduled meeting
    times.
    """

    @staticmethod
    def _from_json(lst):
        if lst is None:
            return None
        return Schedule(sessions=lst)

    def __init__(self, sessions=None):
        """
        Construct a new course `Schedule`. By default it is empty. If you
        pass `sessions`, it should be an iterable containing `Session`
        objects to add to the `Schedule`.
        """
        self._sessions = set()
        if sessions is not None:
            for session in sessions:
                self.add_session(session)

    def add_session(self, session):
        """
        Add a `Session` to this course `Schedule`. If the session already
        exists, print a warning and do nothing.
        """
        if session in self._sessions:
            log.warn("add_session got same session more than once: {}", session)
        self._sessions.add(session)

    def _to_json(self):
        lst = [s.to_json() for s in self._sessions]
        lst.sort()
        return lst

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self._sessions == other._sessions

    def __le__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return sorted(self._sessions) < sorted(other._sessions)

    def __hash__(self):
        return hash(tuple(sorted(self._sessions)))

    def __str__(self):
        return ", ".join(str(s) for s in sorted(self._sessions))


@functools.total_ordering
class Course:
    """
    Class representing a university course, the core abstraction of
    Hyperschedule. Each course is displayed as a separate object on
    the frontend. Courses may not have multiple sections; sections are
    instead represented by multiple `Course` objects.
    """

    @staticmethod
    def _from_json(obj):
        return Course(
            code=obj["courseCode"],
            name=obj["courseName"],
            description=obj["courseDescription"],
            schedule=Schedule.from_json(obj["courseSchedule"]),
            instructors=obj["courseInstructors"],
            num_credits=obj["courseCredits"],
            enrollment_status=obj["courseEnrollmentStatus"],
            num_seats_filled=obj["courseSeatsFilled"],
            num_seats_total=obj["courseSeatsTotal"],
            waitlist_length=obj["courseWaitlistLength"],
            sort_key=obj["courseSortKey"],
            mutual_exclusion_key=obj["courseMutualExclusionKey"],
        )

    def __init__(
        self,
        code=None,
        name=None,
        description=None,
        schedule=None,
        instructors=None,
        num_credits=None,
        enrollment_status=None,
        num_seats_filled=None,
        num_seats_total=None,
        waitlist_length=None,
        sort_key=None,
        mutual_exclusion_key=None,
    ):
        """
        Construct a new `Course`. By default most of the attributes
        are unset, including the required ones.

        The `code`, if given, is a unique string identifying this
        course (section) within the current term. It is displayed on
        the frontend. This field is mandatory; set it with `set_code`
        if you do not pass it here.

        The `name`, if given, is a human-readable name for the course
        as a string. It is displayed on the frontend. This field is
        optional; Hyperschedule will just display the course code if
        you omit it.

        The `description`, if given, is a free-form short description
        for the course as a string. It is displayed on the frontend.
        This field is optional.

        The `instructors`, if given, are a list of strings naming the
        people who will the course. This list may be empty, and
        providing the field is optional. No particular format is
        enforced, although "Lastname, Firstname" is suggested.

        The `num_credits`, `enrollment_status`, `num_seats_filled`,
        `num_seats_total`, and `waitlist_length` fields are all
        optional. `num_credits` is a nonnegative real number
        indicating how many credit-hours (or equivalent) the course
        yields. This is used to display the total number of credits on
        a schedule in the frontend. `enrollment_status` is an
        arbitrary string (for example, "open", "closed", or
        "waitlisted"). `num_seats_filled`, `num_seats_total`, and
        `waitlist_length` pertain to how many seats are available for
        registration in the course. They are all non-negative
        integers. No constraints are enforced amongst these values; in
        particular, it is allowed for more seats to be filled than are
        available.

        The `sort_key` and `mutual_exclusion_key` are also optional.
        They are used in place of enforcing any particular format for
        the course code. Both values are optional. If provided, they
        should be lists of JSON primitives (strings, integers,
        floating-point numbers, booleans, or nulls). `sort_key`
        determines (by lexicographic comparison) the order of courses
        in search results on the frontend. If it is not provided, then
        courses are sorted by lexicographic comparison on their course
        codes. `mutual_exclusion_key` determines which pairs of
        courses may not be simultaneously registered for without
        starring (usually, different sections of the same course). Any
        two courses with the same `mutual_exclusion_key` cannot be
        simultaneously registered for. (However, no constraints at all
        are enforced on registration for courses that have no
        `mutual_exclusion_key` set.)
        """
        self._code = None
        self._name = None
        self._description = None
        self._schedule = None
        self._instructors = None
        self._num_credits = None
        self._enrollment_status = None
        self._num_seats_filled = None
        self._num_seats_total = None
        self._waitlist_length = None
        self._sort_key = None
        self._mutual_exclusion_key = None
        if code is not None:
            self.set_code(code)
        if name is not None:
            self.set_name(name)
        if description is not None:
            self.set_description(description)
        if schedule is not None:
            self.set_schedule(schedule)
        if instructors is not None:
            self.set_instructors(instructors)
        if num_credits is not None:
            self.set_num_credits(num_credits)
        if enrollment_status is not None:
            self.set_enrollment_status(enrollment_status)
        if num_seats_filled is not None:
            self.set_num_seats_filled(num_seats_filled)
        if num_seats_total is not None:
            self.set_num_seats_total(num_seats_total)
        if waitlist_length is not None:
            self.set_waitlist_length(waitlist_length)
        if sort_key is not None:
            self.set_sort_key(sort_key)
        if mutual_exclusion_key is not None:
            self.set_mutual_exclusion_key(mutual_exclusion_key)

    def set_code(self, code):
        """
        Set the course code. If you didn't provide a course code when
        constructing the `Course`, you must call this method. The
        course code can be any string, but it must be unique within
        any given term. Also, since the course code is displayed on
        the frontend, it should be human-readable.
        """
        if not isinstance(code, str):
            raise ImplementorError("set_code got non-string: {}", code)
        self._code = code

    def set_name(self, name):
        """
        Set the course name. This may be any string. It should be
        human-readable.
        """
        if not isinstance(name, str):
            raise ImplementorError("set_name got non-string: {}", name)
        self._name = name

    def set_description(self, description):
        """
        Set the course description. This may be any string.
        """
        if not isinstance(description, str):
            raise ImplementorError("set_description got non-string: {}", description)
        self._description = description

    def set_schedule(self, schedule):
        """
        Set the course schedule. This must be a `Schedule` object.
        """
        if not isinstance(schedule, Schedule):
            raise ImplementorError("set_schedule got non-Schedule: {}", schedule)
        self._schedule = schedule

    def set_instructors(self, instructors):
        """
        Set the list of instructors. This must be a list of strings.
        No particular format is enforced for the names of instructors,
        although "Lastname, Firstname" is suggested as a common
        standard.
        """
        self._instructors = set()
        for instructor in instructors:
            if not isinstance(instructor, str):
                raise ImplementorError("set_instructors got non-string: {}", instructor)
            if instructor in self._instructors:
                log.warn(
                    "set_instructors got same instructor more than once: {}", instructor
                )
            self._instructors.add(instructor)

    def set_num_credits(self, num_credits):
        """
        Set the number of credits or credit hours for the course. This
        may be any nonnegative integer or floating-point number.
        """
        if not isinstance(num_credits, numbers.Real):
            raise ImplementorError("set_num_credits got non-number: {}", num_credits)
        if num_credits < 0:
            raise ImplementorError(
                "set_num_credits got negative number: {}", num_credits
            )
        self._num_credits = num_credits

    def set_enrollment_status(self, enrollment_status):
        """
        Set the enrollment status of the course. This may be any string,
        although typically there should be a small number of possible
        values for any given scraper (for example, "open", "closed",
        or "waitlisted").
        """
        if not isinstance(enrollment_status, str):
            raise ImplementorError(
                "set_enrollment_status got non-string: {}", enrollment_status
            )
        self._enrollment_status = enrollment_status

    def set_num_seats_filled(self, num_seats_filled):
        """
        Set the number of seats which have been filled during
        registration. The value must be a nonnegative integer. This
        may exceed the number of seats available.
        """
        if not isinstance(num_seats_filled, int):
            raise ImplementorError(
                "set_num_seats_filled got non-integer: {}", num_seats_filled
            )
        if num_seats_filled < 0:
            raise ImplementorError(
                "set_num_seats_filled got negative number: {}", num_seats_filled
            )
        self._num_seats_filled = num_seats_filled

    def set_num_seats_total(self, num_seats_total):
        """
        Set the total number of seats available during registration. The
        value must be a nonnegative integer. This need not be as large
        as the number of seats filled.
        """
        if not isinstance(num_seats_total, int):
            raise ImplementorError(
                "set_num_seats_total got non-integer: {}", num_seats_total
            )
        if num_seats_total < 0:
            raise ImplementorError(
                "set_num_seats_total got negative number: {}", num_seats_total
            )
        self._num_seats_total = num_seats_total

    def set_waitlist_length(self, waitlist_length):
        """
        Set the waitlist length. The value must be a nonnegative integer.
        """
        if not isinstance(waitlist_length, int):
            raise ImplementorError(
                "set_waitlist_length got non-integer: {}", waitlist_length
            )
        if waitlist_length < 0:
            raise ImplementorError(
                "set_waitlist_length got negative number: {}", waitlist_length
            )
        self._waitlist_length = waitlist_length

    def set_sort_key(self, sort_key):
        """
        Set the course sort key. This is a list of JSON primitives
        (string, integer, floating-point, boolean, null) which is used
        in a lexicographic sort to determine which order the courses
        will appear in search results on the frontend. If it is
        omitted, then courses are sorted instead lexicographically by
        their course codes.
        """
        if not isinstance(sort_key, list):
            raise ImplementorError("set_sort_key got non-list: {}", sort_key)
        for item in sort_key:
            if not util.is_primitive(item):
                raise ImplementorError("set_sort_key got non-primitive: {}", item)
        self._sort_key = sort_key

    def set_mutual_exclusion_key(self, mutual_exclusion_key):
        """
        Set the mutual exclusion key for the course. This is a list of
        JSON primitives (string, integer, floating-point, boolean,
        null). If two courses both have mutual exclusion keys set and
        the keys are the same, then they will not both be scheduled
        simultaneously in any given schedule on the frontend.
        """
        if not isinstance(mutual_exclusion_key, list):
            raise ImplementorError(
                "set_mutual_exclusion_key got non-list: {}", mutual_exclusion_key
            )
        for item in mutual_exclusion_key:
            if not util.is_primitive(item):
                raise ImplementorError(
                    "set_mutual_exclusion_key got non-primitive: {}", item
                )
        self._mutual_exclusion_key = mutual_exclusion_key

    def _check_valid(self):
        """
        Raise `ImplementorError` if the course code is not set.
        """
        if self._code is None:
            raise ImplementorError("Course missing code")

    def _to_json(self):
        return {
            "courseCode": self._code,
            "courseName": self._name,
            "courseDescription": self._description,
            "courseSchedule": self._schedule,
            "courseInstructors": self._instructors,
            "courseCredits": self._num_credits,
            "courseEnrollmentStatus": self._enrollment_status,
            "courseSeatsFilled": self._num_seats_filled,
            "courseSeatsTotal": self._num_seats_total,
            "courseWaitlistLength": self._waitlist_length,
            "courseSortKey": self._sort_key,
            "courseMutualExclusionKey": self._mutual_exclusion_key,
        }

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self._code,
            self._name,
            self._description,
            self._schedule,
            self._instructors,
            self._num_credits,
            self._enrollment_status,
            self._num_seats_filled,
            self._num_seats_total,
            self._waitlist_length,
            self._sort_key,
            self._mutual_exclusion_key,
        ) == (
            other._code,
            other._name,
            other._description,
            other._schedule,
            other._instructors,
            other._num_credits,
            other._enrollment_status,
            other._num_seats_filled,
            other._num_seats_total,
            other._waitlist_length,
            other._sort_key,
            other._mutual_exclusion_key,
        )

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self._sort_key,
            self._code,
            self._name,
            self._description,
            self._schedule,
            self._instructors,
            self._num_credits,
            self._enrollment_status,
            self._num_seats_filled,
            self._num_seats_total,
            self._waitlist_length,
            self._mutual_exclusion_key,
        ) < (
            other._sort_key,
            other._code,
            other._name,
            other._description,
            other._schedule,
            other._instructors,
            other._num_credits,
            other._enrollment_status,
            other._num_seats_filled,
            other._num_seats_total,
            other._waitlist_length,
            other._mutual_exclusion_key,
        )

    def __hash__(self):
        return hash(
            (
                self._sort_key,
                self._code,
                self._name,
                self._description,
                self._schedule,
                self._instructors,
                self._num_credits,
                self._enrollment_status,
                self._num_seats_filled,
                self._num_seats_total,
                self._waitlist_length,
                self._mutual_exclusion_key,
            )
        )

    def __str__(self):
        parts = []
        if self._code is not None:
            parts.append(self._code)
        if self._name is not None:
            parts.append('"{}"'.format(self._name))
        if self._schedule is not None:
            parts.append(str(self._schedule))
        return " ".join(parts)


class Term:
    """
    Class representing a term. Each course occurs during exactly one
    term, and the Hyperschedule frontend displays courses from only
    one term at a time.
    """

    @staticmethod
    def _from_json(obj):
        return Term(
            code=obj["termCode"], sort_key=obj["termSortKey"], name=obj["termName"]
        )

    def __init__(self, code=None, name=None, sort_key=None):
        """
        Construct a new `Term` object. All fields are mandatory, and
        should be passed as keyword arguments.

        `code` is a string uniquely identifying the term universally
        for the scraper. `name` is a human-readable name for the term.
        `sort_key` is a list of JSON primitives (string, integer,
        floating-point, boolean, or null) which imposes a total
        lexicographic ordering on all term objects which might be
        produced by a scraper.
        """
        if not isinstance(code, str):
            raise ImplementorError("Term got non-string code: {}", code)
        self._code = code
        if not isinstance(name, str):
            raise ImplementorError("Term got non-string name: {}", name)
        self._name = name
        if not isinstance(sort_key, list):
            raise ImplementorError("Term got non-list sort key: {}", sort_key)
        for item in sort_key:
            if not util.is_primitive(item):
                raise ImplementorError(
                    "Term got non-primitive item in sort key: {}", item
                )
        self._sort_key = sort_key

    def _to_json(self):
        return {
            "termCode": self._code,
            "termName": self._name,
            "termSortKey": self._sort_key,
        }

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._code, self._name, self._sort_key) == (
            other._code,
            other._name,
            other._sort_key,
        )

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._code, self._name, self._sort_key) < (
            other._code,
            other._name,
            other._sort_key,
        )

    def __hash__(self):
        return hash((self._code, self._name, self._sort_key))

    def __str__(self):
        return '{} "{}"'.format(self._code, self._name)


class ScraperResult:
    """
    Class representing the result of running a scraper. Conceptually,
    it contains two things: a set of `Course` objects, and a `Term`
    object.
    """

    @staticmethod
    def _from_json(self, obj):
        return ScraperResult(term=obj["term"], courses=obj["courses"])

    def __init__(self, term=None, courses=None):
        """
        Construct a new `ScraperResult`. Both arguments must be set for
        the result to be valid, but you can do that later by calling
        `add_course` and `set_term`.

        If `term` is set, it should be a `Term` object representing
        the term during which the `courses` are offered.

        If `courses` is set, it should be an iterable containing
        `Course` objects to return from the scraper. The courses need
        not have all their information populated right away, if you
        have implemented the `refine` method on your `Scraper`
        subclass.
        """
        self._term = None
        self._courses = {}
        if term is not None:
            self.set_term(term)
        if courses is not None:
            for course in courses:
                self.add_course(course)

    def add_course(self, course):
        """
        Add a `Course` to the `ScraperResult`. It should be distinct from
        all courses previously added.
        """
        if not isinstance(course, Course):
            raise ImplementorError("add_course got non-course: {}", course)
        code = course.get_code()
        if code in self._courses:
            log.warn("multiple courses with same code: {}", code)
        self._courses[code] = course

    def set_term(self, term):
        """
        Set the `Term` of the `ScraperResult`. This is the term during
        which the courses in the `ScraperResult` are offered.
        """
        if not isinstance(term, Term):
            raise ImplementorError("set_term got non-term: {}", term)
        self._term = term

    def _to_json(self):
        return {"courses": self._courses, "term": self._term}

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._courses, self._term) == (other._courses, other._term)

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._courses, self._term) < (other._courses, other._term)

    def __hash__(self):
        return hash((tuple(sorted(self._courses)), self._term))

    def __str__(self):
        return "Scraper result for {} with {} course{}".format(
            self._term, len(self._courses), "" if len(self._courses) == 1 else "s"
        )


class Scraper(abc.ABC):
    """
    Class representing a Hyperschedule scraper. Subclass this to
    create a scraper for a new school.
    """

    def __init__(self, **kwargs):
        """
        Construct a new instance of the scraper. The keyword arguments
        `kwargs` come from the `options` key of the configuration file
        "scrapers.json" in the root of this repository.
        """

    @abc.abstractmethod
    def run(self):
        """
        Retrieve basic course data from the university's course database,
        and return it as a `ScraperResult` object.

        This method should not take longer than 15 minutes to run. If
        it takes too long, consider fetching only basic information
        about each course and then implementing the optional `refine`
        method to fill in the rest of the information for each course
        later.
        """

    def refine(self, course):
        """
        Fetch additional information about a course from the university's
        course database. The `course` argument is a `Course` object,
        and the return value should be another `Course` object. You
        may mutate `course` directly if you wish, and may return None
        as a shorthand for returning the original `Course` object.

        This method is optional. It is useful when it is possible to
        fetch basic information about all the courses initially, but
        filling in the rest of the details requires fetching
        information individually for each course. If you implement
        this method, then Hyperschedule will handle calling it
        automatically in parallel and stopping before the 15-minute
        timeout, and then resuming where it left off the next time the
        scraper is called.
        """
