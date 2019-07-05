"""
Utility library for Hyperschedule scrapers. Contains the
maintainer-facing API for writing a scraper.
"""

import abc
import datetime

import dateparser


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


class MaintainerError(Exception):
    """
    Exception raised when the maintainer misuses the Hyperschedule
    library.
    """

    def __init__(self, msg, *args, **kwargs):
        """
        Construct a new `MaintainerError`, passing the `msg`, `args`, and
        `kwargs` to `str.format`.
        """
        super().__init__(msg.format(*args, **kwargs))


class Date:
    """
    Class representing a specific day of the year. Immutable.
    """

    def _from_json(self, string):
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
            raise MaintainerError("Date got invalid string: {}", string) from None
        self.year = dt.year
        self.month = dt.month
        self.day = dt.day

    def _to_json(self):
        return "{}-{}-{}".format(self.year, self.month, self.day)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.year, self.month, self.day) == (other.year, other.month, other.day)

    def __hash__(self):
        return hash((self.year, self.month, self.day))

    def __str__(self):
        return "{}-{}-{}".format(self.year, self.month, self.day)


class Time:
    """
    Class representing a specific time of day. Immutable.
    """

    def _from_json(self, string):
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
            raise MaintainerError("Time got invalid string: {}", string) from None
        self.hour = dt.hour
        self.minute = dt.minute

    def _to_json(self):
        return "{:02d}:{:02d}".format(self.hour, self.minute)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.hour, self.minute) == (other.hour, other.minute)

    def __hash__(self):
        return hash((self.hour, self.minute))

    def __str__(self):
        hour = (self.hour - 1) % 12 + 1
        minute = self.minute
        ampm = "AM" if self.hour < 12 else "PM"
        return "{}:{} {}".format(hour, minute, ampm)


class Weekdays:
    """
    Class representing some subset of the days of the week (Monday
    through Sunday).
    """

    CHARS = "MTWRFSU"

    def _from_json(string):
        return Weekdays(string)

    # TODO: _from_json for the rest of the classes

    def __init__(self, days=None):
        """
        Construct a new set of `Weekdays`. By default it is empty. If you
        pass `days`, it should be an iterable containing days to add
        to the `Weekdays`, for example "MWF".
        """
        self.days = set()
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
            raise MaintainerError("add_day got invalid day: {}", day)
        if day in days:
            log.warn("add_day got same day more than once: {}", day)
        days.add(day)

    def _check_valid(self):
        """
        Raise `MaintainerError` unless this `Weekdays` object is suitable
        for embedding in other objects.
        """
        if not self.days:
            raise MaintainerError("Weekdays has no days")

    def _to_json(self):
        return "".join(sorted(self.days, key=lambda d: Weekdays.CHARS.index(d)))

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.days == other.days

    def __hash__(self):
        return hash(tuple(sorted(self.days)))

    def __str__(self):
        return "".join(sorted(self.days, key=lambda d: Weekdays.CHARS.index(d)))


class Subterm:
    """
    Class representing either the entirety of a term or only a
    sub-part, in the abstract. Immutable. This class represents
    "full-term", "first half-term", "second half-term", and so on,
    without making reference to any specific term. For those simple
    cases, consider using the constants `FullTerm`, `FirstHalfTerm`,
    `SecondHalfTerm`, and so on.
    """

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
            raise MaintainerError("Subterm got no arguments")
        if not any(subterms):
            raise MaintainerError("Subterm got no truthy arguments: {}", subterms)
        self.subterms = tuple(map(bool, subterms))

    def _to_json(self):
        return list(self.subterms)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.subterms == other.subterms

    def __hash__(self):
        return hash(tuple(self.subterms))

    def __str__(self):
        fractions = [
            "{}/{}".format(idx + 1, len(self.subterms))
            for idx, included in enumerate(self.subterms)
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


class Session:
    """
    Class representing a single recurring meeting time for a course.
    """

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
        self.start_date = None
        self.end_date = None
        self.weekdays = None
        self.start_time = None
        self.end_time = None
        self.subterm = FullTerm
        self.location = None
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
            raise MaintainerError("set_start_date got non-Date: {}", start_date)
        self.start_date = start_date
        self._check_dates()

    def set_end_date(self, end_date):
        """
        Set the end `Date` for this course session. No course meetings
        will occur after the `end_date`.
        """
        if not isinstance(end_date, Date):
            raise MaintainerError("set_end_date got non-Date: {}", end_date)
        self.end_date = end_date
        self._check_dates()

    def set_weekdays(self, weekdays):
        """
        Set the `Weekdays` for this course session. The course will only
        meet on these days. You must call this method if you did not
        pass `weekdays` when constructing the `Session`.
        """
        if not isinstance(weekdays, Weekdays):
            raise MaintainerError("set_weekdays got non-Weekdays: {}", weekdays)
        weekdays._check_valid()
        self.weekdays = weekdays

    def set_start_time(self, start_time):
        """
        Set the start `Time` for this course session.
        """
        if not isinstance(start_time, Time):
            raise MaintainerError("set_start_time got non-Time: {}", start_time)
        self.start_time = start_time
        self._check_times()

    def set_end_time(self, end_time):
        """
        Set the end `Time` for this course session.
        """
        if not isinstance(end_time, Time):
            raise MaintainerError("set_end_time got non-Time: {}", end_time)
        self.end_time = end_time
        self._check_times()

    def set_subterm(self, subterm):
        """
        Set the `Subterm` for this course session. By default, courses are
        `FullTerm`.
        """
        if not isinstance(subterm, Subterm):
            raise MaintainerError("set_subterm got non-Subterm: {}", subterm)
        self.subterm = subterm

    def set_location(self, location):
        """
        Set the location for this course session, a string.
        """
        if not isinstance(location, Location):
            raise MaintainerError("set_location got non-string: {}", location)
        self.location = location

    def _check_dates(self):
        """
        Raise `MaintainerError` if `start_date` and `end_date` are both
        set and `start_date` is not before `end_date`.
        """
        if self.start_date is not None and self.end_date is not None:
            if self.start_date >= self.end_date:
                raise MaintainerError(
                    "Session start date not before end date: {} >= {}",
                    self.start_date,
                    self.end_date,
                )

    def _check_times(self):
        """
        Raise `MaintainerError` if `start_time` and `end_time` are both
        set and `start_time` is not before `end_time`.
        """
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise MaintainerError(
                    "Session start time not before end time: {} >= {}",
                    self.start_time,
                    self.end_time,
                )

    def _check_valid(self):
        """
        Raise `MaintainerError` if `start_time`, `end_time`, and
        `weekdays` are not all set.
        """
        if self.start_time is None:
            raise MaintainerError("Session missing start time")
        if self.end_time is None:
            raise MaintainerError("Session missing end time")
        if self.weekdays is None:
            raise MaintainerError("Session missing Weekdays")

    def _to_json(self):
        return {
            "scheduleStartDate": self.start_date,
            "scheduleEndDate": self.end_date,
            "scheduleWeekdays": self.weekdays,
            "scheduleStartTime": self.start_time,
            "scheduleEndTime": self.end_time,
            "scheduleSubterm": self.subterm,
            "scheduleLocation": self.location,
        }

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (
            self.start_date,
            self.end_date,
            self.weekdays,
            self.start_time,
            self.end_time,
            self.subterm,
            self.location,
        ) == (
            other.start_date,
            other.end_date,
            other.weekdays,
            other.start_time,
            other.end_time,
            other.subterm,
            other.location,
        )

    def __hash__(self):
        return hash(
            (
                self.start_date,
                self.end_date,
                self.weekdays,
                self.start_time,
                self.end_time,
                self.subterm,
                self.location,
            )
        )

    def __str__(self):
        groups = []
        group = []
        if self.weekdays is not None:
            group.append(str(weekdays))
        if self.start_time is not None:
            group.append(str(self.start_time))
        if self.start_time is not None and self.end_time is not None:
            group.append("-")
        if self.end_time is not None:
            group.append(str(self.end_time))
        if group:
            groups.append(group)
            group = []
        if self.start_date is not None:
            group.append(str(self.start_date))
        if self.start_date is not None and self.end_date is not None:
            group.append("-")
        if self.end_date is not None:
            group.append(str(self.end_date))
        if group:
            groups.append(group)
            group = []
        if self.subterm != FullTerm:
            groups.append(str(self.subterm))
        if self.location is not None:
            groups.append(self.location)
        return ", ".join(" ".join(group) for group in groups)


class Schedule:
    """
    Class representing the set of all of a course's scheduled meeting
    times.
    """

    def __init__(self, sessions=None):
        """
        Construct a new course `Schedule`. By default it is empty. If you
        pass `sessions`, it should be an iterable containing `Session`
        objects to add to the `Schedule`.
        """

    # TODO: implement


class Course:
    """
    Class representing a university course, the core abstraction of
    Hyperschedule. Each course is displayed as a separate object on
    the frontend. Courses may not have multiple sections; sections are
    instead represented by multiple `Course` objects.
    """

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
        TODO: write
        """

    # TODO: implement


class Term:
    """
    Class representing a term. Each course occurs during exactly one
    term, and the Hyperschedule frontend displays courses from only
    one term at a time.
    """

    # TODO: implement


class ScraperResult:
    """
    Class representing the result of running a scraper. Conceptually,
    it contains two things: a set of `Course` objects, and a `Term`
    object.
    """

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
        self.term = None
        self.courses = {}
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
            raise MaintainerError("add_course got non-course: {}", course)
        code = course.get_code()
        if code in self.courses:
            log.warn("multiple courses with same code: {}", code)
        self.courses[code] = course

    def set_term(self, term):
        """
        Set the `Term` of the `ScraperResult`. This is the term during
        which the courses in the `ScraperResult` are offered.
        """
        if not isinstance(term, Term):
            raise MaintainerError("set_term got non-term: {}", term)
        self.term = term


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
