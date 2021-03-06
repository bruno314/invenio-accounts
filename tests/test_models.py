# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Test invenio-accounts models."""

from __future__ import absolute_import

from sqlalchemy import inspect

from invenio_accounts import InvenioAccounts, testutils
from invenio_accounts.models import SessionActivity
from invenio_accounts.views import blueprint


def test_session_activity_model(app):
    """Test SessionActivity model."""
    ext = InvenioAccounts(app)
    app.register_blueprint(blueprint)

    # SessionActivity table is in the datastore database.
    datastore = app.extensions['invenio-accounts'].datastore
    inspector = inspect(datastore.db.engine)
    assert 'accounts_user_session_activity' in inspector.get_table_names()

    user = testutils.create_test_user()

    # Create a new SessionActivity object, put it in the datastore.
    session_activity = SessionActivity(user_id=user.get_id(),
                                       sid_s="teststring")
    database = datastore.db

    # the `created` field is magicked in via the Timestamp mixin class
    assert not session_activity.created
    assert not session_activity.id
    database.session.add(session_activity)
    # Commit it to the books.
    database.session.commit()
    assert session_activity.created
    assert session_activity.id
    assert len(user.active_sessions) == 1

    # Now how does this look on the user object?
    assert session_activity == user.active_sessions[0]

    session_two = SessionActivity(user_id=user.get_id(),
                                  sid_s="testring_2")
    database.session.add(session_two)
    # Commit it to the books.
    database.session.commit()

    assert len(user.active_sessions) == 2
    # Check #columns in table
    queried = database.session.query(SessionActivity)
    assert queried.count() == 2
    active_sessions = queried.all()
    assert session_activity.sid_s in [x.sid_s for x in active_sessions]
    assert session_two in queried.filter(
        SessionActivity.sid_s == session_two.sid_s)
    assert queried.count() == 2  # `.filter` doesn't change the query

    # Test session deletion
    session_to_delete = user.active_sessions[0]
    database.session.delete(session_to_delete)
    assert len(user.active_sessions) == 2  # Not yet updated.
    assert queried.count() == 1
    # Deletion is visible on `user` once database session is commited.
    database.session.commit()
    assert len(user.active_sessions) == 1
    assert user.active_sessions[0].sid_s != session_to_delete.sid_s
